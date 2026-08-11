"""Destilación de información: clasifica cada item en una de las 27 coordenadas.

Cascada progresiva (de barato a caro):
    1. Heurística determinista (keywords contra los descriptores de nodos.yaml) — ms.
    2. Embeddings locales (bge-m3, /api/embed) + similitud coseno con los 27 descriptores — ms.
    3. Clasificador DeepSeek (maestro) — resuelve lo que la heurística no cubre.
La dimensión (m/l/s) del clasificador local qwen3 fue retirada del proyecto por
errores; los embeddings bge-m3 se mantienen. Devolver None nunca rompe el ciclo.
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path

import yaml

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo

DIMENSIONES = ("m", "l", "s")
DIM_LABEL = {"m": "material", "l": "razón lógica", "s": "social"}

_OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
_EMBED_MODELO = os.getenv("LLM_LOCAL_EMBED", "bge-m3")

#: Alumno/maestro: registrar desacuerdos del clasificador de dimensión (DeepSeek)
#: para construir un dataset de destilación. (El clasificador local qwen3 fue
#: retirado por errores; bge-m3 sigue disponible para embeddings.)
_ALUMNO_MAESTRO = os.getenv("DIM_ALUMNO_MAESTRO", "1") == "1"

_STOPWORDS = {
    "los", "las", "el", "la", "un", "una", "unos", "unas", "y", "o", "u",
    "de", "del", "en", "con", "por", "para", "que", "su", "sus", "es", "son",
    "al", "a", "no", "se", "lo", "como", "tambien", "entre", "sobre",
}


def _ruta_config() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "config" / "nodos.yaml"


def nodos_validos() -> list[str]:
    ruta = _ruta_config()
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return [n["id"] for n in data.get("nodos", []) if "id" in n]


def _descriptores_27() -> list[tuple[str, str, str]]:
    """[(nodo_id, dimensión, descriptor)] de las 27 coordenadas."""
    ruta = _ruta_config()
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out: list[tuple[str, str, str]] = []
    for n in data.get("nodos", []):
        nid = n.get("id")
        if not nid:
            continue
        for dim in DIMENSIONES:
            texto = (n.get(f"{dim}_desc") or "").strip()
            if texto:
                out.append((nid, dim, texto))
    return out


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return texto.encode("ascii", "ignore").decode("ascii")


def _tokens(texto: str) -> set[str]:
    return {
        w for w in re.findall(r"\w+", _norm(texto))
        if len(w) >= 3 and w not in _STOPWORDS
    }


# ─── LLM local (Ollama) ────────────────────────────────────────


def _llamada_ollama(ruta: str, payload: dict, timeout: int = 30):
    req = urllib.request.Request(
        _OLLAMA_URL + ruta,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _ruta_alumno() -> Path:
    return (
        Path(__file__).resolve().parent.parent.parent.parent
        / "data" / "alumno" / "destilacion.jsonl"
    )


def _registrar_alumno_maestro(
    item: ItemInformativo,
    alumno: tuple[str, str] | None,
    maestro: tuple[str, str] | None,
    origen: str,
) -> None:
    """Registra el par (item, etiqueta alumno, etiqueta maestro) en jsonl.

    Solo se registra cuando el alumno y el maestro difieren o el alumno falló
    (desacuerdos = señal de caso metafórico/estructural). El registro es un
    append; desactivable con DIM_ALUMNO_MAESTRO=0.
    """
    if not _ALUMNO_MAESTRO:
        return
    if alumno == maestro:
        return
    try:
        texto = f"{item.titulo} {item.contenido}".strip()
        fila = {
            "ts": datetime.now().isoformat(),
            "origen": origen,
            "item_id": item.id,
            "titulo": item.titulo,
            "texto": texto[:1000],
            "alumno": {"nodo": alumno[0], "dim": alumno[1]} if alumno else None,
            "maestro": {"nodo": maestro[0], "dim": maestro[1]} if maestro else None,
            "modelo_alumno": "heuristica/embeddings (bge-m3)",
        }
        ruta = _ruta_alumno()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
        logger.debug(f"Alumno/maestro registrado ({origen}): {alumno} vs {maestro}")
    except Exception as exc:
        logger.debug(f"No se pudo registrar alumno/maestro: {exc}")


def _embedding(texto: str) -> list[float] | None:
    try:
        data = _llamada_ollama("/api/embed", {"model": _EMBED_MODELO, "input": texto}, timeout=30)
        emb = data.get("embeddings") or data.get("embedding")
        if isinstance(emb, list) and emb and isinstance(emb[0], float):
            return emb
        if isinstance(emb, list) and emb:
            return emb[0]
        return None
    except Exception as e:
        logger.debug(f"Embedding local no disponible: {e}")
        return None


_vectores_descriptores_cache: dict[tuple[str, str], list[float]] | None = None


def _vectores_descriptores() -> dict[tuple[str, str], list[float]]:
    global _vectores_descriptores_cache
    if _vectores_descriptores_cache is None:
        _vectores_descriptores_cache = {}
        for nid, dim, texto in _descriptores_27():
            v = _embedding(texto)
            if v:
                _vectores_descriptores_cache[(nid, dim)] = v
        if _vectores_descriptores_cache and len(_vectores_descriptores_cache) < 27:
            logger.warning(
                f"Embeddings de descriptores: {len(_vectores_descriptores_cache)}/27 disponibles"
            )
    return _vectores_descriptores_cache


def _cos(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def _usar_ollama() -> bool:
    return os.getenv("DIMENSIONES_OLLAMA", "1") == "1"


# ─── Niveles de la destilación ─────────────────────────────────


def _nivel_heuristica(texto: str) -> tuple[str, str] | None:
    toks = _tokens(texto)
    if not toks:
        return None
    mejor: tuple[str, str, int] | None = None
    for nid, dim, desc in _descriptores_27():
        coincidencias = len(toks & _tokens(desc))
        if coincidencias > 0 and (mejor is None or coincidencias > mejor[2]):
            mejor = (nid, dim, coincidencias)
    if mejor is None:
        return None
    return (mejor[0], mejor[1])


_UMBRAL_EMB = float(os.getenv("DIM_UMBRAL_EMB", "0.24"))


def _aviso_pila(cajon: str) -> None:
    """Ruta crítica: alerta una sola vez por proceso si el stack local falla."""
    if not getattr(_aviso_pila, "_emitido", False):
        logger.warning(
            f"Stack local (Ollama) no disponible para '{cajon}' — usando "
            f"protocolo de emergencia (DeepSeek) y/o heurística."
        )
        _aviso_pila._emitido = True


def _nivel_llm_deepseek(texto: str) -> tuple[str, str] | None:
    """Fallback de emergencia: clasifica (nodo, dim) con la API de DeepSeek."""
    if os.getenv("DIM_FALLBACK_DEEPSEEK", "1") != "1":
        return None
    nodos = nodos_validos()
    if not nodos:
        return None
    prompt = (
        'Clasifica el siguiente texto en una de las coordenadas (nodo, dimensión) '
        'de una matriz cultural de 9 nodos x 3 dimensiones.\n'
        'Guías de dimensión:\n'
        '- m (material): recursos físicos, dinero, infraestructura, máquinas, bienes.\n'
        '- l (razón lógica): ideas, ideología, filosofía, leyes, doctrina, discurso, teoría.\n'
        '- s (social): personas organizadas, comunidad, sindicatos, redes, familia, participación, protestas.\n'
        'Elige s cuando el tema trate de interacción o colectivos de personas, '
        'no solo de ideas. No uses l solo por defecto.\n'
        'Responde SOLO con JSON exacto: {"nodo":"","dim":""}.\n'
        f'Nodos válidos (usa estos identificadores exactos): {", ".join(nodos)}.\n'
        f"Texto a clasificar: {texto[:1000]}"
    )
    try:
        from topologia.models.llm import LLMClient

        parsed = LLMClient().generar_json(prompt, temperatura=0.1, max_tokens=120)
        nodo = str(parsed.get("nodo", "")).strip().upper()
        dim = str(parsed.get("dim", "")).strip().lower()
        if nodo in nodos and dim in DIMENSIONES:
            return (nodo, dim)
        logger.debug(f"Coordenada inválida de DeepSeek: {parsed}")
    except Exception as exc:
        logger.warning(f"DeepSeek fallback de clasificación falló: {exc}")
    return None


def _nivel_embeddings(texto: str, umbral: float | None = None) -> tuple[str, str] | None:
    umbral = _UMBRAL_EMB if umbral is None else umbral
    if not _usar_ollama():
        return None
    vec = _embedding(texto)
    if not vec:
        return None
    mejores = _vectores_descriptores()
    if not mejores:
        return None
    mejor: tuple[str, str, float] | None = None
    for (nid, dim), dv in mejores.items():
        s = _cos(vec, dv)
        if s >= umbral and (mejor is None or s > mejor[2]):
            mejor = (nid, dim, s)
    if mejor is None:
        return None
    return (mejor[0], mejor[1])


# ─── API pública ───────────────────────────────────────────────


_maestros_consultados = 0
_MAX_MAESTRO = int(os.getenv("DIM_ALUMNO_MAX_MAESTRO", "20"))


def _consultar_maestro(item: ItemInformativo, texto: str) -> tuple[str, str] | None:
    """Consulta a DeepSeek (maestro) para comparar con el alumno estructural.

    Acotada por DIM_ALUMNO_MAX_MAESTRO por proceso para no gastar la API en
    todos los items; registra el desacuerdo cuando difiere del alumno.
    """
    global _maestros_consultados
    if not _ALUMNO_MAESTRO:
        return None
    if _maestros_consultados >= _MAX_MAESTRO:
        return None
    if os.getenv("DIM_FALLBACK_DEEPSEEK", "1") != "1":
        return None
    _maestros_consultados += 1
    return _nivel_llm_deepseek(texto)


def _aplicar_resultado(item: ItemInformativo, resultado: tuple[str, str] | None) -> tuple[str, str] | None:
    """Guarda (nodo, dim) en el item. Solo fija nodo_sugerido si el item no lo tiene."""
    if not resultado:
        return None
    nodo, dim = resultado
    item.dimension_sugerida = dim
    if not getattr(item, "nodo_sugerido", None):
        item.nodo_sugerido = nodo  # type: ignore[attr-defined]
    return resultado


def _clasificar_dimension_con_maestro(item: ItemInformativo, texto: str) -> tuple[str, str] | None:
    """Cascada completa: heurística → embeddings (alumno) → maestro.

    El alumno es el clasificador estructural primario (abstracción metafórica).
    El maestro (DeepSeek) se consulta en una muestra acotada para comparar y
    registrar desacuerdos en data/alumno/destilacion.jsonl.
    """
    for nivel in (_nivel_heuristica, _nivel_embeddings):
        alumno = nivel(texto)
        if alumno and _aplicar_resultado(item, alumno):
            maestro = _consultar_maestro(item, texto)
            if maestro and maestro != alumno:
                _registrar_alumno_maestro(item, alumno, maestro, origen="alumno")
            return item.nodo_sugerido, item.dimension_sugerida

    maestro = _nivel_llm_deepseek(texto)
    if maestro and _aplicar_resultado(item, maestro):
        _registrar_alumno_maestro(item, None, maestro, origen="fallback")
        return item.nodo_sugerido, item.dimension_sugerida
    return None


def clasificar_dimension(item: ItemInformativo) -> tuple[str, str] | None:
    """Cascada heurística → embeddings → maestro. Devuelve (nodo, dim) o None."""
    texto = f"{item.titulo} {item.contenido}".strip()
    if not texto:
        return None
    return _clasificar_dimension_con_maestro(item, texto)


def asignar_dimensiones(items: list[ItemInformativo]) -> None:
    """Etiqueta cada item en (nodo, m/l/s).

    Cascada para todos (heurística → embeddings → maestro). Los items que ya
    traen nodo solo reciben dimensión; los sin nodo (descubiertos/RSS)
    reciben nodo+dim y así entran en la cobertura de las 27 coordenadas.
    """
    for item in items:
        texto = f"{item.titulo} {item.contenido}".strip()
        if not texto:
            continue
        if os.getenv("DIM_LLM_TODO", "0") == "1" and not getattr(item, "nodo_sugerido", None):
            _clasificar_llm_primario(item, texto)
        else:
            clasificar_dimension(item)


def _clasificar_llm_primario(item: ItemInformativo, texto: str) -> tuple[str, str] | None:
    for nivel in (_nivel_llm_deepseek, _nivel_heuristica, _nivel_embeddings):
        if _aplicar_resultado(item, nivel(texto)):
            return item.nodo_sugerido, item.dimension_sugerida
    return None


def cobertura_por_dimension(items: list[ItemInformativo]) -> dict[str, dict[str, int]]:
    """Conteo de items por (nodo, dimensión), las 27 coordenadas con valor 0 por defecto."""
    cobertura = {nid: {d: 0 for d in DIMENSIONES} for nid in nodos_validos()}
    for item in items:
        nodo = item.nodo_sugerido
        dim = item.dimension_sugerida
        if nodo in cobertura and dim in DIMENSIONES:
            cobertura[nodo][dim] += 1
    return cobertura


def dimensiones_ciegas(cobertura: dict[str, dict[str, int]]) -> dict[str, list[str]]:
    """{nodo: [dimensiones con 0 items]}."""
    ciegas: dict[str, list[str]] = {}
    for nodo, dims in cobertura.items():
        falta = [d for d, c in dims.items() if c == 0]
        if falta:
            ciegas[nodo] = falta
    return ciegas


def releer_ciegas(
    items: list[ItemInformativo],
    ciegas: dict[str, list[str]],
    cobertura: dict[str, dict[str, int]],
    max_por_coord: int = 6,
) -> int:
    """Re-lectura: llena coordenadas ciegas con items ya existentes.

    Por cada (nodo, dimensión) ciega revisa hasta `max_por_coord` items del
    nodo con DeepSeek; el primero que asigne a esa dimensión se re-etiqueta.
    No roba el único ocupante de otra coordenada. Sin búsquedas.
    Devuelve cuántas coordenadas se cubrieron.
    """
    rellenas = 0
    for nodo, dims in ciegas.items():
        nodo_items = [it for it in items if getattr(it, "nodo_sugerido", None) == nodo]
        if not nodo_items:
            continue
        for dim in dims:
            for it in nodo_items[:max_por_coord]:
                actual = getattr(it, "dimension_sugerida", None)
                if actual and cobertura.get(nodo, {}).get(actual, 0) == 1:
                    continue
                texto = f"{it.titulo} {it.contenido}".strip()
                if not texto:
                    continue
                resultado = _nivel_llm_deepseek(texto)
                if resultado and resultado[1] == dim:
                    it.dimension_sugerida = dim
                    rellenas += 1
                    break
    return rellenas


_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def query_para_dimension(nodo_id: str, dim: str) -> str:
    """Query dirigida: el descriptor de la coordenada + referente chileno + actualidad."""
    hoy = datetime.now()
    mes = _MESES[hoy.month - 1]
    for nid, d, texto in _descriptores_27():
        if nid == nodo_id and d == dim:
            return f"{texto} Chile noticias {mes} {hoy.year}"
    return f"{nodo_id} {dim} Chile noticias {mes} {hoy.year}"


def queries_para_ciegas(ciegas: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        nodo: [query_para_dimension(nodo_id=nodo, dim=d) for d in dims]
        for nodo, dims in ciegas.items()
    }