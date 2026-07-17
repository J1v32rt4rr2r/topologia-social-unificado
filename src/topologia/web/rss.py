from __future__ import annotations

from datetime import datetime

import feedparser

from topologia.models.schemas import ItemInformativo


FUENTES_RSS = [
    "https://news.google.com/rss?hl=es-419&gl=CL&ceid=CL:es-419",
    "https://feeds.emol.com/emol/rss/portada",
    "https://www.latercera.com/feed/",
]


def obtener_items(limite: int = 20) -> list[ItemInformativo]:
    items: list[ItemInformativo] = []
    for fuente_url in FUENTES_RSS:
        try:
            feed = feedparser.parse(fuente_url)
            for entry in feed.entries[:limite]:
                items.append(ItemInformativo(
                    id=f"rss-{len(items)}",
                    titulo=entry.get("title", ""),
                    fuente=fuente_url.split("/")[2],
                    contenido=entry.get("summary", entry.get("description", "")),
                    url=entry.get("link", ""),
                    fecha=datetime.now(),
                    tags=["rss"],
                ))
        except Exception:
            continue
    return items
