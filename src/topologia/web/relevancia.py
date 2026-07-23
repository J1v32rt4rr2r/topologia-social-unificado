from __future__ import annotations

import json

from topologia.logger import logger
from topologia.models.llm import LLMClient
from topologia.models.schemas import EstrategiaRecoleccion, ItemInformativo
from topologia.web.brechas import NODOS_CULTURALES
from topologia.web.search import buscar as buscar_ddg

_IGNORAR_TERMINOS = [
    "nueva york", "trump", "biden", "putin", "ucrania", "rusia",
    "premier league", "nba", "nfl", "bitcoin", "dr. cong",
    "elecciones ee.uu", "guerra en ucrania", "casa blanca",
    "pentágono", "otan", "gaza", "israel", "hamás",
]

_IGNORAR_FUENTES = [
    "cnn.com", "bbc.com", "nytimes.com", "theguardian.com",
    "washingtonpost.com", "reuters.com",
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


def generar_queries(
    estrategia: EstrategiaRecoleccion,
    max_por_nodo: int = 3,
) -> dict[str, list[str]]:
    llm = LLMClient()
    queries: dict[str, list[str]] = {}

    # Nodos con brecha: generar queries alternativas con LLM
    for nodo_id in estrategia.nodos_con_brecha:
        descripcion = _descripcion_nodo(nodo_id)
        prompt = (
            f"Eres un periodista de investigación especializado en la realidad chilena.\n"
            f"El tema de investigación '{nodo_id}' estudia {descripcion} en Chile.\n"
            f"Ha sido difícil encontrar noticias relevantes para este tema.\n"
            f"Genera {max_por_nodo} búsquedas en español, concretas y actuales, que podrían\n"
            f"encontrar noticias chilenas sobre {nodo_id}. Cada búsqueda debe\n"
            f"incluir 'Chile' o un referente chileno específico.\n"
            f"Responde solo como JSON list, ej: [\"query1\", \"query2\"]"
        )
        try:
            resultado = llm.generar_json(prompt, temperatura=0.7, max_tokens=512)
            if isinstance(resultado, list):
                queries[nodo_id] = resultado[:max_por_nodo]
            elif isinstance(resultado, dict):
                vals = list(resultado.values())
                queries[nodo_id] = vals[:max_por_nodo]
            logger.info(f"Queries generadas para {nodo_id}: {queries.get(nodo_id, [])}")
        except Exception as e:
            logger.warning(f"No se pudieron generar queries para {nodo_id}: {e}")

    # Nodos prioritarios: generar queries específicas
    for nodo_id in estrategia.nodos_prioritarios:
        if nodo_id in queries:
            continue
        dim = estrategia.dimensiones_inestables.get(nodo_id, None)
        descripcion = _descripcion_nodo(nodo_id)
        dim_extra = ""
        if dim:
            dim_extra = (
                f"Este nodo muestra inestabilidad en la dimensión {dim}.\n"
                f"Genera búsquedas que aborden específicamente el aspecto {dim} "
                f"(material/lógica/social) de {nodo_id} en Chile.\n"
            )
        prompt = (
            f"Eres un periodista de investigación especializado en la realidad chilena.\n"
            f"El tema de investigación '{nodo_id}' estudia {descripcion} en Chile.\n"
            f"{dim_extra}"
            f"Genera {max_por_nodo} búsquedas en español, concretas, para encontrar\n"
            f"noticias chilenas actuales sobre {nodo_id}.\n"
            f"Responde solo como JSON list."
        )
        try:
            resultado = llm.generar_json(prompt, temperatura=0.5, max_tokens=512)
            if isinstance(resultado, list):
                queries[nodo_id] = resultado[:max_por_nodo]
            elif isinstance(resultado, dict):
                vals = list(resultado.values())
                queries[nodo_id] = vals[:max_por_nodo]
            logger.info(f"Queries generadas para {nodo_id}: {queries.get(nodo_id, [])}")
        except Exception as e:
            logger.warning(f"No se pudieron generar queries para {nodo_id}: {e}")

    return queries


def recolectar_por_queries(
    queries: dict[str, list[str]],
    estrategia: EstrategiaRecoleccion,
) -> list[ItemInformativo]:
    items: list[ItemInformativo] = []
    vistos: set[str] = set()

    for nodo_id, nodo_queries in queries.items():
        max_res = 8 if nodo_id in set(estrategia.nodos_prioritarios) else 5
        for query in nodo_queries:
            try:
                resultados = buscar_ddg(query, max_resultados=max_res)
                for r in resultados:
                    if r.id not in vistos:
                        r.nodo_sugerido = nodo_id  # type: ignore[attr-defined]
                        vistos.add(r.id)
                        items.append(r)
            except Exception as e:
                logger.warning(f"Error en búsqueda '{query}': {e}")

    logger.info(f"Recolección dirigida: {len(items)} items desde {len(queries)} nodos")
    return items


def _descripcion_nodo(nodo_id: str) -> str:
    descs = {
        "ECONOMIA": "recursos económicos, mercado, producción, inflación, comercio en Chile",
        "TRABAJO": "empleo, condiciones laborales, sindicatos, pensiones, sueldo mínimo en Chile",
        "SEXUALIDAD": "sexualidad, reproducción, género, diversidad sexual, educación sexual, derechos reproductivos en Chile",
        "POLITICA": "gobierno, congreso, partidos, leyes, constitución, corrupción en Chile",
        "LENGUAJE": "discurso público, propaganda, medios, narrativas políticas, lenguaje en Chile",
        "ETICA_ESTETICA": "arte, cultura, ética, estética, festivales, moral, cine chileno",
        "TECNOLOGIA": "innovación, ciencia, litio, hidrógeno verde, IA, startups en Chile",
        "EDUCACION": "educación, universidades, reforma educacional, estudiantes, SIMCE en Chile",
        "RELIGION": "iglesia, religión, evangélicos, catolicismo, espiritualidad en Chile",
    }
    return descs.get(nodo_id, nodo_id)
