from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo


_cache: dict[str, tuple[float, list[ItemInformativo]]] = {}
CACHE_DURACION = 600
_ultima_llamada: float = 0.0
_DELAY_ENTRE_LLAMADAS = 1.0


def _esperar_rate_limit() -> None:
    global _ultima_llamada
    ahora = time.time()
    diff = ahora - _ultima_llamada
    if diff < _DELAY_ENTRE_LLAMADAS:
        time.sleep(_DELAY_ENTRE_LLAMADAS - diff)
    _ultima_llamada = time.time()


def buscar(palabras_clave: str, max_resultados: int = 10) -> list[ItemInformativo]:
    cache_key = palabras_clave.lower().strip()
    if cache_key in _cache:
        timestamp, resultados = _cache[cache_key]
        if time.time() - timestamp < CACHE_DURACION:
            return resultados

    resultados: list[ItemInformativo] = []
    try:
        from duckduckgo_search import DDGS
        _esperar_rate_limit()
        with DDGS() as ddgs:
            for r in ddgs.text(palabras_clave, max_results=max_resultados):
                resultados.append(ItemInformativo(
                    id=f"search-{len(resultados)}",
                    titulo=r.get("title", ""),
                    fuente="duckduckgo",
                    contenido=r.get("body", ""),
                    url=r.get("href", ""),
                    fecha=datetime.now(),
                    tags=["search", palabras_clave],
                ))
    except ImportError:
        logger.warning("duckduckgo_search no instalado")
    except Exception as e:
        logger.debug(f"Error en búsqueda '{palabras_clave}': {e}")

    _cache[cache_key] = (time.time(), resultados)
    return resultados


def buscar_para_estudio(patron_id: str, palabras_clave: str, max_r: int = 15) -> list[ItemInformativo]:
    terminos = f"{patron_id} {palabras_clave}"
    return buscar(terminos, max_resultados=max_r)
