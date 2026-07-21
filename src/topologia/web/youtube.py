"""
Módulo de consulta a YouTube Data API v3 para obtener videos chilenos
por ventana de fecha (Fase 4: discursiva de masas).

La API key se lee de YOUTUBE_API_KEY en .env (nunca hardcodeada en el código).
Requiere: pip install python-dotenv (ya instalado en el proyecto).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from topologia.logger import logger
from topologia.models.schemas import ItemInformativo

# Carga variables de entorno (.env); seguro si ya fue cargado por llm.py
load_dotenv()

# Identificación del proyecto para transparencia (cabecera HTTP)
USER_AGENT = (
    "TopologiaSocial/2.0 "
    "(Proyecto de investigacion sociologica; "
    "monitoreo de clima cultural chileno; "
    "https://github.com/J1v32rt4rr2r/topologia-social-unificado; "
    "contacto: j1v32rt4rr2r@proton.me)"
)

# Endpoint de la YouTube Data API v3
BASE = "https://www.googleapis.com/youtube/v3/search"

# Control de rate limiting: 1 segundo entre llamadas
_ultima_llamada: float = 0.0
_DELAY = 1.0


def _obtener_api_key() -> str:
    """Lee la API key desde la variable de entorno (cargada por dotenv en llm.py)."""
    key = os.getenv("YOUTUBE_API_KEY", "")
    if not key:
        logger.warning("YOUTUBE_API_KEY no configurada en .env")
    return key


def _esperar() -> None:
    """Rate limiting simple entre llamadas a la API."""
    global _ultima_llamada
    ahora = time.time()
    diff = ahora - _ultima_llamada
    if diff < _DELAY:
        time.sleep(_DELAY - diff)
    _ultima_llamada = time.time()


def buscar(
    query: str = "Chile",
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    max_resultados: int = 50,
) -> list[ItemInformativo]:
    """
    Busca videos en YouTube sobre Chile en una ventana de fecha.

    Args:
        query: Término de búsqueda (default "Chile").
        fecha_inicio: ISO 8601 (ej. "2026-07-18T00:00:00Z").
        fecha_fin:   ISO 8601 (ej. "2026-07-19T00:00:00Z").
        max_resultados: Máximo de videos a retornar (default 50, max 50 por página).

    Returns:
        Lista de ItemInformativo con título, canal, URL, descripción y fecha.
    """
    api_key = _obtener_api_key()
    if not api_key:
        return []

    params: dict[str, Any] = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_resultados, 50),
        "relevanceLanguage": "es",
        "regionCode": "CL",
        "key": api_key,
    }
    if fecha_inicio:
        params["publishedAfter"] = fecha_inicio
    if fecha_fin:
        params["publishedBefore"] = fecha_fin

    resultados: list[ItemInformativo] = []

    try:
        _esperar()
        url = f"{BASE}?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=15) as resp:
            data: dict = json.loads(resp.read().decode("utf-8"))

        items = data.get("items", [])
        logger.info(
            f"YouTube: {len(items)} videos para '{query}' "
            f"[{fecha_inicio or '—'}..{fecha_fin or '—'}]"
        )

        for i, item in enumerate(items):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", f"unknown-{i}")
            titulo = snippet.get("title", "")
            desc = snippet.get("description", "")[:500]
            canal = snippet.get("channelTitle", "")
            published = snippet.get("publishedAt", "")

            resultados.append(ItemInformativo(
                id=f"yt-{video_id}",
                titulo=titulo,
                fuente=f"youtube/{canal}",
                contenido=desc,
                url=f"https://www.youtube.com/watch?v={video_id}",
                fecha=_parse_iso(published),
                tags=["youtube", query],
            ))

    except Exception as e:
        logger.error(f"YouTube API error: {e}")

    return resultados


def _parse_iso(s: str) -> datetime:
    """Convierte string ISO 8601 a datetime con timezone."""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.now()
