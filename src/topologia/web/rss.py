from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import feedparser
import yaml

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _limpiar_html(texto: str) -> str:
    texto = _HTML_TAG_RE.sub(" ", texto)
    texto = texto.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"").replace("&#39;", "'").replace("&nbsp;", " ").replace("&#xa0;", " ")
    texto = _WS_RE.sub(" ", texto).strip()
    return texto


def _cargar_feeds() -> list[str]:
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "feeds.yaml"
    if not ruta.exists():
        logger.warning(f"feeds.yaml no encontrado en {ruta}, usando defaults")
        return [
            "https://news.google.com/rss?hl=es-419&gl=CL&ceid=CL:es-419",
            "https://feeds.emol.com/emol/rss/portada",
            "https://www.latercera.com/feed/",
        ]
    with ruta.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)
    urls = []
    for feed in config.get("rss", []):
        if feed.get("activo", True):
            urls.append(feed["url"])
    if not urls:
        logger.warning("No hay feeds activos en feeds.yaml, usando defaults")
        urls = [
            "https://news.google.com/rss?hl=es-419&gl=CL&ceid=CL:es-419",
        ]
    return urls


def obtener_items(limite: int = 20) -> list[ItemInformativo]:
    fuentes = _cargar_feeds()
    items: list[ItemInformativo] = []
    vistos: set[str] = set()

    for fuente_url in fuentes:
        try:
            feed = feedparser.parse(fuente_url)
            fuente_nombre = fuente_url.split("/")[2]
            for entry in feed.entries[:limite]:
                link = entry.get("link", "")
                if link in vistos:
                    continue
                vistos.add(link)
                titulo = _limpiar_html(entry.get("title", ""))
                contenido = _limpiar_html(entry.get("summary", entry.get("description", "")))
                items.append(ItemInformativo(
                    id=f"rss-{len(items)}",
                    titulo=titulo,
                    fuente=fuente_nombre,
                    contenido=contenido,
                    url=link,
                    fecha=datetime.now(),
                    tags=["rss", fuente_nombre],
                ))
            logger.info(f"RSS {fuente_nombre}: {len(feed.entries[:limite])} items obtenidos")
        except Exception as e:
            logger.error(f"Error en RSS {fuente_url}: {e}")
            continue

    logger.info(f"RSS total: {len(items)} items únicos de {len(fuentes)} fuentes")
    return items
