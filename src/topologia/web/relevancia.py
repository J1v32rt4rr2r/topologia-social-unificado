from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from topologia.logger import logger
from topologia.models.llm import LLMClient
from topologia.models.schemas import EstrategiaRecoleccion, ItemInformativo
from topologia.web.compuestos import actualizar_termino, frases_para_nodo
from topologia.web.search import buscar as buscar_ddg

_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

_DIMENSIONES = ("m", "l", "s")

_IGNORAR_TERMINOS = [
    "nueva york", "trump", "biden", "putin", "ucrania", "rusia",
    "premier league", "nba", "nfl", "bitcoin", "dr. cong",
    "elecciones ee.uu", "guerra en ucrania", "casa blanca",
    "pentágono", "otan", "gaza", "israel", "hamás",
]

_IGNORAR_FUENTES = [
    "cnn.com", "bbc.com", "nytimes.com", "theguardian.com",
    "washingtonpost.com", "reuters.com",
    # Enciclopedias y contenido de referencia atemporal (sin fecha)
    "wikipedia.org", "wikisource.org", "wikidata.org", "britannica.com",
]


def _tiene_termino_ignorado(item: ItemInformativo) -> bool:
    texto = (item.titulo + " " + item.contenido).lower()
    for term in _IGNORAR_TERMINOS:
        if term in texto:
            return True
    return False


def _fuente_ignorada(item: ItemInformativo) -> bool:
    fuente = (item.fuente or item.url or "").lower()
    for ign in _IGNORAR_FUENTES:
        if ign in fuente:
            return True
    return False


def puntuar_relevancia(
    items: list[ItemInformativo],
    estrategia: EstrategiaRecoleccion,
) -> list[ItemInformativo]:
    if not items:
        return []

    umbral = estrategia.umbral_relevancia
    nodos_prioritarios = set(estrategia.nodos_prioritarios)

    items_filtrados = []
    for item in items:
        if _tiene_termino_ignorado(item):
            continue
        if _fuente_ignorada(item):
            continue

        # Score base: 0.5
        score = 0.5

        fuente_baja = item.fuente.lower() if item.fuente else ""
        if fuente_baja in (f.lower() for f in estrategia.fuentes_ruidosas):
            score -= 0.2
        if fuente_baja in (f.lower() for f in estrategia.fuentes_activas):
            score += 0.2

        # Si el item tiene tag de nodo prioritario, sube score
        if hasattr(item, "nodo_sugerido") and item.nodo_sugerido in nodos_prioritarios:
            score += 0.3

        if score >= umbral:
            items_filtrados.append(item)

    logger.info(
        f"Filtro de relevancia: {len(items)} → {len(items_filtrados)} "
        f"(umbral={umbral})"
    )
    return items_filtrados


def _prompt_dimensiones(nodo_id: str, dim: str | None) -> str:
    """Bloque de contexto con las 3 dimensiones (27 totales) del nodo."""
    descs = _descripciones_dimensiones(nodo_id)
    lineas = (
        f"El nodo '{nodo_id}' se estudia en 3 dimensiones:\n"
        f"  - material: {descs['m'] or 'no definida'}\n"
        f"  - razón lógica (ideología, cosmovisión): {descs['l'] or 'no definida'}\n"
        f"  - social (redes y relaciones): {descs['s'] or 'no definida'}\n"
    )
    if dim in _DIMENSIONES:
        lineas += (
            f"Este nodo presenta inestabilidad en la dimensión '{dim}': "
            f"genera búsquedas enfocadas específicamente en esa dimensión.\n"
        )
    else:
        lineas += (
            "Genera una búsqueda concreta POR CADA dimensión (m/l/s), "
            "priorizando la razón lógica (cambios ideológicos, de cosmovisión "
            "o de discurso) en Chile.\n"
        )
    return lineas


def _prompt_compuestos(nodo_id: str) -> str:
    """Bloque con combinaciones de nodos (intersecciones) para el prompt."""
    frases = frases_para_nodo(nodo_id, max_frases=4)
    lineas = (
        "Los temas se cruzan entre nodos culturales, p. ej. 'política económica'\n"
        "(Política x Economía), 'educación sexual' (Educación x Sexualidad),\n"
        "'política religiosa' (Política x Religión).\n"
    )
    if frases:
        lineas += f"Para este nodo usa frases como: {', '.join(frases)}.\n"
    lineas += (
        "Incluye al menos una búsqueda que combine este nodo con otro\n"
        "(intersección), no solo el tema aislado.\n"
    )
    return lineas


def generar_queries(
    estrategia: EstrategiaRecoleccion,
    max_por_nodo: int = 3,
) -> dict[str, list[str]]:
    llm = LLMClient()
    queries: dict[str, list[str]] = {}
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    regla_actualidad = (
        f"Es {fecha_hoy}. Busca SOLO noticias publicadas en los últimos 7 días.\n"
        f"Evita artículos de referencia, enciclopedias (p. ej. Wikipedia), "
        f"páginas institucionales atemporales o contenido sin fecha de publicación.\n"
    )

    # Nodos con brecha: generar queries alternativas con LLM
    for nodo_id in estrategia.nodos_con_brecha:
        descripcion = _descripcion_nodo(nodo_id)
        prompt = (
            f"Eres un periodista de investigación especializado en la realidad chilena.\n"
            f"El tema de investigación '{nodo_id}' estudia {descripcion} en Chile.\n"
            f"Ha sido difícil encontrar noticias relevantes para este tema.\n"
            f"{_prompt_dimensiones(nodo_id, None)}"
            f"{_prompt_compuestos(nodo_id)}"
            f"{regla_actualidad}"
            f"Genera {max_por_nodo} búsquedas en español, concretas y actuales, que podrían\n"
            f"encontrar noticias chilenas sobre {nodo_id}. Cada búsqueda debe\n"
            f"incluir 'Chile' o un referente chileno específico.\n"
            f"Responde solo como JSON list, ej: [\"query1\", \"query2\"]"
        )
        queries[nodo_id] = _queries_con_llm(llm, prompt, nodo_id, max_por_nodo)

    # Nodos prioritarios: generar queries específicas
    for nodo_id in estrategia.nodos_prioritarios:
        if nodo_id in queries:
            continue
        dim = estrategia.dimensiones_inestables.get(nodo_id, None)
        descripcion = _descripcion_nodo(nodo_id)
        prompt = (
            f"Eres un periodista de investigación especializado en la realidad chilena.\n"
            f"El tema de investigación '{nodo_id}' estudia {descripcion} en Chile.\n"
            f"{_prompt_dimensiones(nodo_id, dim)}"
            f"{_prompt_compuestos(nodo_id)}"
            f"{regla_actualidad}"
            f"Genera {max_por_nodo} búsquedas en español, concretas, para encontrar\n"
            f"noticias chilenas actuales sobre {nodo_id}.\n"
            f"Responde solo como JSON list."
        )
        queries[nodo_id] = _queries_con_llm(llm, prompt, nodo_id, max_por_nodo)

    return queries


def _query_llm_aceptable(query: str) -> bool:
    """Descarta ruido que el LLM repite (etiquetas de dimensión, instrucciones)."""
    texto = query.strip()
    if len(texto) < 5:
        return False
    norm = _norm_query(texto)
    if norm in {"m", "l", "s"}:
        return False
    if norm in {"material", "social", "razon lógica", "razon logica", "razon"}:
        return False
    # Marcas fuertes de eco de instrucción o etiqueta conceptual (cualquier longitud)
    marcas = ("priorizando", "dimensión", "dimension", "razon lógica", "razon logica")
    for pal in marcas:
        if pal in norm:
            return False
    if len(texto) < 25 and any(p in norm for p in ("busca la", "busca cambios")):
        return False
    return True


def _norm_query(texto: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode("ascii")


def _queries_con_llm(
    llm: LLMClient,
    prompt: str,
    nodo_id: str,
    max_por_nodo: int,
) -> list[str]:
    """Queries del LLM con fallback estático por dimensión si falla o vacío."""
    try:
        resultado = llm.generar_json(prompt, temperatura=0.7, max_tokens=512)
        generadas = [q for q in _extraer_strings(resultado, max_por_nodo * 2) if _query_llm_aceptable(q)]
        generadas = generadas[:max_por_nodo]
        if generadas:
            logger.info(f"Queries generadas para {nodo_id}: {generadas}")
            return generadas
    except Exception as e:
        logger.warning(f"No se pudieron generar queries para {nodo_id}: {e}")
    estaticas = _queries_estaticas_dimensiones(nodo_id) + _queries_compuestas(nodo_id)
    estaticas = estaticas[: max_por_nodo * 2]
    logger.info(f"Queries estáticas por dimensión para {nodo_id}: {estaticas}")
    return estaticas


def recolectar_por_queries(
    queries: dict[str, list[str]],
    estrategia: EstrategiaRecoleccion,
    max_por_query: int = 0,
) -> list[ItemInformativo]:
    items: list[ItemInformativo] = []
    vistos: set[str] = set()

    for nodo_id, nodo_queries in queries.items():
        if max_por_query > 0:
            max_res = max_por_query
        else:
            max_res = 8 if nodo_id in set(estrategia.nodos_prioritarios) else 5
        for query in nodo_queries:
            try:
                resultados = buscar_ddg(actualizar_termino(query), max_resultados=max_res)
                for r in resultados:
                    if r.id not in vistos:
                        r.nodo_sugerido = nodo_id  # type: ignore[attr-defined]
                        vistos.add(r.id)
                        items.append(r)
            except Exception as e:
                logger.warning(f"Error en búsqueda '{query}': {e}")

    logger.info(f"Recolección dirigida: {len(items)} items desde {len(queries)} nodos")
    return items


def _extraer_strings(resultado: Any, max_items: int) -> list[str]:
    if isinstance(resultado, list):
        strings = []
        for item in resultado:
            if isinstance(item, str):
                strings.append(item)
            elif isinstance(item, dict):
                for v in item.values():
                    if isinstance(v, str):
                        strings.append(v)
        return strings[:max_items]
    elif isinstance(resultado, dict):
        vals = [str(v) for v in resultado.values() if isinstance(v, (str, int, float))]
        return vals[:max_items]
    return []


_DESCRIPCIONES_ESTATICAS = {
    "ECONOMIA": "recursos económicos, mercado, producción, inflación, comercio en Chile",
    "TRABAJO": "empleo, condiciones laborales, sindicatos, pensiones, sueldo mínimo en Chile",
    "SEXUALIDAD": "sexualidad, reproducción, género, diversidad sexual, educación sexual, derechos reproductivos en Chile",
    "POLITICA": "gobierno, congreso, partidos, leyes, constitución, corrupción en Chile",
    "LENGUAJE": "discurso público, propaganda, medios, narrativas políticas, lenguaje en Chile",
    "ETICA_ESTETICA": "arte, cultura, ética, estética, festivales, moral, cine chileno",
    "TECNOLOGIA": "innovación tecnológica, ciencia, inteligencia artificial, startups, litio, hidrógeno verde, energía renovable, digitalización, internet, ciberseguridad en Chile",
    "EDUCACION": "educación, universidades, reforma educacional, estudiantes, SIMCE en Chile",
    "RELIGION": "iglesia, religión, evangélicos, catolicismo, espiritualidad en Chile",
}


def _cargar_nodos() -> dict[str, dict[str, str]]:
    """Carga config/nodos.yaml → {NODO: {m_desc, l_desc, s_desc}}."""
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "nodos.yaml"
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {n["id"]: n for n in data.get("nodos", []) if "id" in n}


def _descripciones_dimensiones(nodo_id: str) -> dict[str, str]:
    """Descripciones de las 27 dimensiones (m/l/s por nodo) desde nodos.yaml.

    m = material (recursos, infraestructura)
    l = razón lógica (ideología, filosofía, discurso)
    s = social (redes, relaciones, instituciones informales)
    """
    nodos = _cargar_nodos()
    info = nodos.get(nodo_id, {})
    descs = {
        "m": info.get("m_desc", ""),
        "l": info.get("l_desc", ""),
        "s": info.get("s_desc", ""),
    }
    if any(descs.values()):
        return descs
    # Fallback: derivar de la descripción estática conocida
    base = _DESCRIPCIONES_ESTATICAS.get(nodo_id, nodo_id)
    return {"m": base, "l": base, "s": base}


def _descripcion_nodo(nodo_id: str) -> str:
    descs = _descripciones_dimensiones(nodo_id)
    partes = [p for p in (descs["m"], descs["l"], descs["s"]) if p]
    if len(set(partes)) == 1:
        return partes[0]
    return " | ".join(partes)


def _queries_estaticas_dimensiones(nodo_id: str) -> list[str]:
    """Una búsqueda concreta por dimensión (m/l/s) del nodo, con actualidad.

    Usa la 'razón lógica' (dimensión l) como foco: es la que mide el sistema.
    """
    descs = _descripciones_dimensiones(nodo_id)
    hoy = datetime.now()
    mes = _MESES[hoy.month - 1]
    queries = []
    for dim, texto in (("m", descs["m"]), ("l", descs["l"]), ("s", descs["s"])):
        if not texto or texto == nodo_id:
            continue
        queries.append(f"{texto} Chile noticias {mes} {hoy.year}")
    if not queries:
        queries.append(f"{nodo_id} Chile noticias {mes} {hoy.year}")
    return queries


def _queries_compuestas(nodo_id: str, max_frases: int = 4) -> list[str]:
    """Frases de combinaciones entre nodos (intersecciones), con actualidad.

    P. ej. para POLITICA: 'política económica Chile noticias agosto 2026'.
    """
    hoy = datetime.now()
    mes = _MESES[hoy.month - 1]
    return [
        f"{frase} Chile noticias {mes} {hoy.year}"
        for frase in frases_para_nodo(nodo_id, max_frases=max_frases)
    ]
