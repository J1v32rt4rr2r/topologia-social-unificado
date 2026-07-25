from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo


_cache: dict[str, tuple[float, list[ItemInformativo]]] = {}
CACHE_DURACION = 600
_ultima_llamada: float = 0.0
_DELAY_ENTRE_LLAMADAS = 2.0

USER_AGENT = (
    "TopologiaSocial/2.0 "
    "(Proyecto de investigacion sociologica; "
    "monitoreo de clima cultural chileno; "
    "https://github.com/J1v32rt4rr2r/topologia-social-unificado; "
    "contacto: j1v32rt4rr2r@proton.me)"
)


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
        from ddgs import DDGS
        _esperar_rate_limit()
        with DDGS() as ddgs:
            for r in ddgs.text(palabras_clave, max_results=max_resultados):
                titulo = r.get("title", "")
                cuerpo = r.get("body", "")
                from topologia.web.rss import _RE_CHILE
                if not _RE_CHILE.search(titulo + " " + (cuerpo or "")):
                    continue
                resultados.append(ItemInformativo(
                    id=f"search-{len(resultados)}",
                    titulo=titulo,
                    fuente="duckduckgo",
                    contenido=cuerpo,
                    url=r.get("href", ""),
                    fecha=datetime.now(),
                    tags=["search", palabras_clave],
                ))
    except ImportError:
        logger.warning("ddgs no instalado")
    except Exception as e:
        logger.warning(f"Error en búsqueda '{palabras_clave}': {e}")

    _cache[cache_key] = (time.time(), resultados)
    return resultados


def buscar_para_estudio(patron_id: str, palabras_clave: str, max_r: int = 15) -> list[ItemInformativo]:
    terminos = f"{patron_id} {palabras_clave}"
    return buscar(terminos, max_resultados=max_r)
