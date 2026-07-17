from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import requests

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo


USER_AGENT = "TopologiaSocial/1.0 (+https://github.com/anomalyco/topologia-social)"
TIMEOUT = 15


FUENTES_BCN: list[dict[str, Any]] = [
    {
        "url": "https://www.bcn.cl/leychice",
        "categoria": "POLITICA",
        "nombre": "Ley Chile",
        "tags": ["bcn", "leyes", "politica"],
    },
    {
        "url": "https://www.bcn.cl/catalogos",
        "categoria": "EDUCACION",
        "nombre": "Catálogos BCN",
        "tags": ["bcn", "catalogos", "educacion"],
    },
]


def _scrapear_titulo(url: str) -> str | None:
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.encoding = resp.apparent_encoding or "utf-8"
        texto = re.sub(r"<[^>]+>", " ", resp.text)
        texto = re.sub(r"\s+", " ", texto).strip()
        palabras_clave = ["Ley", "Chile", "Biblioteca", "Congreso", "BCN"]
        palabras = [p for p in palabras_clave if p.lower() in texto.lower()]
        if palabras:
            return f"BCN: {', '.join(palabras)}"
    except requests.RequestException as e:
        logger.warning(f"BCN error fetching {url}: {e}")
    return None


def _scrapear_contenido(url: str, categoria: str) -> str | None:
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.encoding = resp.apparent_encoding or "utf-8"
        texto = re.sub(r"<script[^>]*>.*?</script>", "", resp.text, flags=re.DOTALL)
        texto = re.sub(r"<style[^>]*>.*?</style>", "", texto, flags=re.DOTALL)
        texto = re.sub(r"<[^>]+>", " ", texto)
        texto = re.sub(r"\s+", " ", texto).strip()
        if len(texto) > 100:
            return texto[:1500]
    except requests.RequestException:
        pass
    return f"Recurso de la Biblioteca del Congreso Nacional. Categoría: {categoria}."


def obtener_items(limite: int = 5) -> list[ItemInformativo]:
    items: list[ItemInformativo] = []
    for cfg in FUENTES_BCN[:limite]:
        titulo = _scrapear_titulo(cfg["url"]) or f"BCN: {cfg['nombre']}"
        contenido = _scrapear_contenido(cfg["url"], cfg["categoria"])
        items.append(ItemInformativo(
            id=f"bcn-{len(items)}",
            titulo=titulo,
            fuente="bcn",
            contenido=contenido or f"Recurso de la Biblioteca del Congreso Nacional. Categoría: {cfg['categoria']}.",
            url=cfg["url"],
            fecha=datetime.now(),
            tags=cfg["tags"] + [cfg["categoria"].lower()],
        ))
    logger.info(f"BCN: {len(items)} items generados")
    return items
