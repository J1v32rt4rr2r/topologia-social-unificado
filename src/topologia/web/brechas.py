from __future__ import annotations

import unicodedata
from pathlib import Path

import yaml

from topologia.models.schemas import EstadoCultural, ItemInformativo

NODOS_CULTURALES = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]

UMBRAL_ITEMS_MINIMOS = 3
UMBRAL_SCORE_PLANO = 0.5

UMBRAL_POR_NODO: dict[str, int] = {
    "RELIGION": 1,
    "TECNOLOGIA": 1,
}


def _cargar_palabras_clave() -> dict:
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "palabras_clave.yaml"
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


_PALABRAS_CACHE: dict | None = None


def _obtener_palabras_clave() -> dict:
    global _PALABRAS_CACHE
    if _PALABRAS_CACHE is None:
        _PALABRAS_CACHE = _cargar_palabras_clave()
    return _PALABRAS_CACHE


def terminos_para_nodo(nodo_id: str) -> list[str]:
    data = _obtener_palabras_clave()
    nodos = data.get("nodos", {})
    info = nodos.get(nodo_id, {})
    return info.get("clasificacion", [nodo_id.lower()])


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _match_parcial(texto: str, terminos: list[str]) -> bool:
    """Coincidencia exacta o parcial (prefijo de 4+ caracteres)."""
    lower = _normalize(texto.lower())
    for t in terminos:
        if _normalize(t.lower()) in lower:
            return True
    for t in terminos:
        nt = _normalize(t.lower())
        if len(nt) >= 4 and nt[:4] in lower:
            return True
    return False


def clasificar_items_por_nodo_semantico(
    items: list[ItemInformativo],
) -> dict[str, list[ItemInformativo]]:
    mapa: dict[str, list[ItemInformativo]] = {}
    todos_asignados: set[int] = set()

    # Primera pasada: items con nodo_sugerido explícito
    sugeridos: dict[str, list[int]] = {}
    for idx, it in enumerate(items):
        ns = getattr(it, "nodo_sugerido", None)
        if ns and ns in NODOS_CULTURALES:
            sugeridos.setdefault(ns, []).append(idx)

    for idx in sum(sugeridos.values(), []):
        todos_asignados.add(idx)

    # Segunda pasada: matching semántico para nodos sin suficientes items sugeridos
    for nodo_id in NODOS_CULTURALES:
        terminos = terminos_para_nodo(nodo_id)
        encontrados: list[ItemInformativo] = []

        for idx in sugeridos.get(nodo_id, []):
            encontrados.append(items[idx])

        for idx, it in enumerate(items):
            if idx in todos_asignados:
                continue
            texto = _normalize((it.titulo + " " + it.contenido).lower())
            if any(_normalize(t.lower()) in texto for t in terminos):
                encontrados.append(it)
                todos_asignados.add(idx)

        umbral = UMBRAL_POR_NODO.get(nodo_id, UMBRAL_ITEMS_MINIMOS)
        if encontrados:
            mapa[nodo_id] = encontrados
            continue

        no_asignados = [it for idx, it in enumerate(items) if idx not in todos_asignados]
        if no_asignados:
            mapa[nodo_id] = no_asignados[:umbral]
            for idx, it in enumerate(items):
                if it in no_asignados[:umbral]:
                    todos_asignados.add(idx)
        else:
            mapa[nodo_id] = items[:umbral]

    return mapa


def detectar_brechas(
    estado: EstadoCultural | None,
    items_por_nodo: dict[str, list[ItemInformativo]] | None = None,
) -> dict[str, dict]:
    brechas: dict[str, dict] = {}
    hay_items = items_por_nodo is not None

    if hay_items:
        for nodo_id in NODOS_CULTURALES:
            items_nodo = items_por_nodo.get(nodo_id, [])
            reales = [it for it in items_nodo if _es_item_relevante(it, nodo_id)]
            umbral = UMBRAL_POR_NODO.get(nodo_id, UMBRAL_ITEMS_MINIMOS)
            brechas[nodo_id] = {
                "total_items": len(items_nodo),
                "items_relevantes": len(reales),
                "tiene_brecha": len(reales) < umbral,
            }

    if estado:
        for n in estado.nodos:
            if n.nodo_id not in brechas:
                brechas[n.nodo_id] = {"total_items": 0, "items_relevantes": 0, "tiene_brecha": True}
            brechas[n.nodo_id]["dimension_m"] = n.dimension_m
            brechas[n.nodo_id]["dimension_l"] = n.dimension_l
            brechas[n.nodo_id]["dimension_s"] = n.dimension_s
            brechas[n.nodo_id]["delta"] = round(n.delta, 1)
            brechas[n.nodo_id]["fragil"] = n.fragil
            brechas[n.nodo_id]["score_plano"] = (
                n.dimension_m == 5.0 and n.dimension_l == 5.0 and n.dimension_s == 5.0
            )

    if not hay_items:
        brechas["_meta"] = {"modo": "standalone", "mensaje": "Sin datos de items (solo estado)"}

    return brechas


def _es_item_relevante(item: ItemInformativo, nodo_id: str) -> bool:
    if getattr(item, "nodo_sugerido", None) == nodo_id:
        return True
    terminos = terminos_para_nodo(nodo_id)
    texto = (item.titulo + " " + item.contenido).lower()
    return _match_parcial(texto, terminos)


def resumir_contexto_noticioso(items_por_nodo: dict[str, list[ItemInformativo]]) -> dict[str, dict]:
    """
    Extrae palabras clave y titulares principales por nodo para anotar gráficos.

    Returns:
        dict[nodo_id] = {
            "keywords": [str, ...],        # 5 términos más frecuentes
            "top_headlines": [str, ...],   # 3 titulares más representativos
            "resumen": str,                # texto corto para interpretación
        }
    """
    from collections import Counter
    import re

    contexto: dict[str, dict] = {}
    for nid, items in items_por_nodo.items():
        if not items:
            continue
        textos = [f"{it.titulo} {it.contenido}" for it in items]
        palabras = re.findall(r'\w{4,}', " ".join(textos).lower())
        comunes = [p for p in palabras if p not in (
            "para", "como", "entre", "sobre", "tiene", "parte", "tras", "este",
            "esta", "esto", "más", "pero", "todo", "cada", "sido", "hace",
            "solo", "gran", "tres", "dos", "una", "con", "del", "que",
        )]
        keywords = [w for w, _ in Counter(comunes).most_common(6)]

        top = items[:3]
        headlines = [it.titulo[:80] for it in top if it.titulo]

        resumen = ""
        if headlines:
            resumen = f"{nid.lower()}: {' · '.join(h for h in headlines[:2])}"

        contexto[nid] = {
            "keywords": keywords,
            "top_headlines": headlines,
            "resumen": resumen,
        }

    # Contexto global: cruce entre nodos con más items
    all_items = []
    for lst in items_por_nodo.values():
        all_items.extend(lst)
    global_keywords = []
    if all_items:
        textos = [f"{it.titulo} {it.contenido}" for it in all_items]
        palabras = re.findall(r'\w{4,}', " ".join(textos).lower())
        comunes = [p for p in palabras if p not in (
            "para", "como", "entre", "sobre", "tiene", "parte", "tras",
        )]
        global_keywords = [w for w, _ in Counter(comunes).most_common(8)]

    contexto["_global"] = {
        "total_items": len(all_items),
        "keywords": global_keywords,
        "resumen": " · ".join(global_keywords[:5]) if global_keywords else "",
    }
    return contexto


def resumen_brechas(brechas: dict[str, dict]) -> str:
    partes: list[str] = []
    contadores = {"con_datos": 0, "sin_datos": 0, "score_plano": 0}
    for nid, info in brechas.items():
        if nid.startswith("_"):
            continue
        if info.get("score_plano") and info.get("total_items", 0) == 0:
            contadores["score_plano"] += 1
            contadores["sin_datos"] += 1
        elif info.get("tiene_brecha"):
            contadores["sin_datos"] += 1
        else:
            contadores["con_datos"] += 1
    partes.append(f"{contadores['con_datos']}/9 nodos con datos suficientes")
    if contadores["score_plano"]:
        planos = [nid for nid, info in brechas.items() if info.get("score_plano")]
        partes.append(f"{contadores['score_plano']} nodos sin datos: {', '.join(planos)}")
    return " | ".join(partes)
