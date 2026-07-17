from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from topologia.models.schemas import ItemInformativo


_cache: dict[str, tuple[float, list[ItemInformativo]]] = {}
CACHE_DURACION = 600


def buscar(palabras_clave: str, max_resultados: int = 10) -> list[ItemInformativo]:
    cache_key = palabras_clave.lower().strip()
    if cache_key in _cache:
        timestamp, resultados = _cache[cache_key]
        if time.time() - timestamp < CACHE_DURACION:
            return resultados

    resultados: list[ItemInformativo] = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(palabras_clave, max_results=max_resultados)):
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
        pass
    except Exception:
        pass

    _cache[cache_key] = (time.time(), resultados)
    return resultados


def buscar_para_estudio(patron_id: str, palabras_clave: str, max_r: int = 15) -> list[ItemInformativo]:
    terminos = f"{patron_id} {palabras_clave}"
    return buscar(terminos, max_resultados=max_r)
