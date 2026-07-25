from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo
from topologia.web.search import buscar


_ULTIMA_PETICION: float = 0.0
_DELAY = 2.0


def _esperar():
    global _ULTIMA_PETICION
    ahora = time.time()
    diff = ahora - _ULTIMA_PETICION
    if diff < _DELAY:
        time.sleep(_DELAY - diff)
    _ULTIMA_PETICION = time.time()


def _cargar_palabras_clave() -> dict:
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "palabras_clave.yaml"
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _generar_queries(periodo: dict) -> list[str]:
    """Genera queries de búsqueda para un periodo histórico.

    Combina la descripción del periodo con términos por nodo cultural.
    """
    pid = periodo["id"]
    desc = periodo.get("descripcion", "")
    anio_inicio = periodo["fecha_inicio"][:4]
    anio_fin = periodo["fecha_fin"][:4]
    anios = f"{anio_inicio}-{anio_fin}" if anio_inicio != anio_fin else anio_inicio

    queries_base = [
        f"Chile {desc} {anios} resumen",
        f"Chile {anios} noticias",
        f"Chile {anios} balance",
    ]

    data = _cargar_palabras_clave()
    nodos = data.get("nodos", {})
    for nid, info in nodos.items():
        terminos = info.get("busqueda_externa", [])
        for t in terminos[:2]:
            queries_base.append(f"{t} {anios}")

    return queries_base


def recolectar_para_periodo(
    periodo: dict,
    max_items: int = 100,
    items_por_query: int = 8,
) -> list[ItemInformativo]:
    """Recolecta resúmenes de noticias para un periodo histórico vía DuckDuckGo.

    Para cada query generada, busca en DuckDuckGo y crea ItemInformativo.
    Mucho más rápido y confiable que Wayback Machine.
    """
    pid = periodo["id"]
    logger.info(f"[{pid}] Generando queries de búsqueda...")
    queries = _generar_queries(periodo)
    logger.info(f"[{pid}] {len(queries)} queries generadas")

    items_totales: list[ItemInformativo] = []
    vistos_url: set[str] = set()
    vistos_contenido: set[str] = set()

    for i, query in enumerate(queries):
        if len(items_totales) >= max_items:
            break

        _esperar()
        logger.info(f"[{pid}] Buscando: '{query[:60]}'")
        try:
            resultados = buscar(query, max_resultados=items_por_query)
        except Exception as e:
            logger.warning(f"[{pid}] Error en búsqueda '{query}': {e}")
            continue

        nuevos = 0
        for r in resultados:
            if len(items_totales) >= max_items:
                break
            if r.url and r.url in vistos_url:
                continue
            vistos_url.add(r.url)
            if r.contenido and r.contenido in vistos_contenido:
                continue
            vistos_contenido.add(r.contenido)

            if not r.contenido or len(r.contenido) < 30:
                continue

            fecha = r.fecha if r.fecha else datetime.now(timezone.utc)
            item = ItemInformativo(
                id=f"rh-{pid}-{len(items_totales)}",
                titulo=(r.titulo or "")[:200],
                fuente=f"resumen_historico:{pid}",
                contenido=r.contenido,
                url=r.url or "",
                fecha=fecha,
                tags=["historico", pid, "resumen"],
            )
            items_totales.append(item)
            nuevos += 1

        if nuevos:
            logger.info(f"[{pid}]  +{nuevos} items de '{query[:40]}'")

    logger.info(
        f"[{pid}] Recolección completada: {len(items_totales)} items "
        f"de {len(queries)} queries"
    )
    return items_totales
