from __future__ import annotations

import time
from pathlib import Path

import yaml

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo
from topologia.web.brechas import NODOS_CULTURALES
from topologia.web.search import buscar


def _cargar_palabras_clave() -> dict:
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "palabras_clave.yaml"
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def recolectar_para_nodo(nodo_id: str, max_items: int = 5) -> list[ItemInformativo]:
    data = _cargar_palabras_clave()
    nodos = data.get("nodos", {})
    info = nodos.get(nodo_id, {})
    terminos = info.get("busqueda_externa", [])

    items: list[ItemInformativo] = []
    vistos: set[str] = set()
    for termino in terminos:
        if len(items) >= max_items:
            break
        resultados = buscar(termino, max_resultados=max_items * 2)
        for r in resultados:
            if r.url and r.url not in vistos:
                vistos.add(r.url)
                r.fuente = f"scraping:{nodo_id.lower()}"
                r.id = f"scrape-{nodo_id.lower()}-{len(items)}"
                r.nodo_sugerido = nodo_id
                items.append(r)
                if len(items) >= max_items:
                    break
    return items


def recolectar_para_brechas(brechas: dict) -> list[ItemInformativo]:
    todos: list[ItemInformativo] = []
    persistentes_sin_datos: list[str] = []
    for i, nid in enumerate(NODOS_CULTURALES):
        info = brechas.get(nid, {})
        score_plano = info.get("score_plano", False)
        tiene_items = info.get("total_items", 0) > 0
        tiene_brecha = info.get("tiene_brecha", True)
        debe_scrapear = score_plano or not tiene_items or tiene_brecha
        if nid == "TECNOLOGIA":
            debe_scrapear = True
        if debe_scrapear:
            if i > 0:
                time.sleep(3)
            max_items = 10 if score_plano else 5
            nuevos = recolectar_para_nodo(nid, max_items=max_items)
            if nuevos:
                logger.info(f"Scraping dirigido para {nid}: {len(nuevos)} items (max={max_items})")
                todos.extend(nuevos)
            else:
                logger.warning(f"Nodo {nid} sin cobertura incluso después de scraping dirigido")
                persistentes_sin_datos.append(nid)
    if persistentes_sin_datos:
        logger.warning(f"Nodos persistentemente sin datos: {', '.join(persistentes_sin_datos)} — considerar agregar fuentes")
    return todos
