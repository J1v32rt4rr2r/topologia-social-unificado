from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests
import yaml

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_CACHE: dict[str, tuple[float, list[ItemInformativo]]] = {}
CACHE_DURACION = 300
TIMEOUT_SEG = 15
USER_AGENT = "TopologiaSocial/1.0 (+https://github.com/anomalyco/topologia-social)"

_FUENTES_CHILENAS = [
    "ciperchile", "elsiglo", "theclinic", "cambio21",
    "elciudadano", "uchile", "trendtic", "gerencia",
]
_RE_CHILE = re.compile(r"\bchile\b|\bchilen[ao]s?\b", re.IGNORECASE)


def _limpiar_html(texto: str) -> str:
    texto = _HTML_TAG_RE.sub(" ", texto)
    for old, new in [
        ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
        ("&quot;", '"'), ("&#39;", "'"), ("&#x27;", "'"),
        ("&nbsp;", " "), ("&#xa0;", " "), ("&ndash;", "-"),
        ("&mdash;", "--"), ("&iexcl;", "¡"), ("&iquest;", "¿"),
        ("&aacute;", "á"), ("&eacute;", "é"), ("&iacute;", "í"),
        ("&oacute;", "ó"), ("&uacute;", "ú"), ("&ntilde;", "ñ"),
        ("&Aacute;", "Á"), ("&Eacute;", "É"), ("&Iacute;", "Í"),
        ("&Oacute;", "Ó"), ("&Uacute;", "Ú"), ("&Ntilde;", "Ñ"),
    ]:
        texto = texto.replace(old, new)
    texto = _WS_RE.sub(" ", texto).strip()
    return texto


def _extraer_fecha(entry: Any) -> datetime:
    for campo in ("published_parsed", "updated_parsed"):
        parsed = entry.get(campo)
        if parsed:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except Exception:
                continue
    return datetime.now(timezone.utc)


def _fuente_real(entry: Any, feed_url: str) -> str:
    source = entry.get("source")
    if source and hasattr(source, "get"):
        valor = source.get("title") or source.get("value")
        if valor:
            return _limpiar_html(str(valor))
    return feed_url.split("/")[2]


def _cargar_config() -> dict:
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "feeds.yaml"
    if not ruta.exists():
        return {}
    with ruta.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _obtener_feeds_activos(config: dict) -> list[dict]:
    feeds = config.get("rss", [])
    if not feeds:
        return [{"url": "https://news.google.com/rss?hl=es-419&gl=CL&ceid=CL:es-419"}]
    return [f for f in feeds if f.get("activo", True)]


def _obtener_fuentes_locales(config: dict) -> list[dict]:
    return [f for f in config.get("fuentes_locales", []) if f.get("activo", False)]


def _fetch_rss(url: str) -> list[ItemInformativo]:
    try:
        resp = requests.get(url, timeout=TIMEOUT_SEG, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
    except requests.RequestException as e:
        logger.error(f"RSS error de red en {url}: {e}")
        return []
    except Exception as e:
        logger.error(f"RSS error al parsear {url}: {e}")
        return []

    items: list[ItemInformativo] = []
    vistos: set[str] = set()

    for entry in feed.entries:
        try:
            link = entry.get("link", "")
            if not link or link in vistos:
                continue
            vistos.add(link)

            titulo = _limpiar_html(entry.get("title", ""))
            contenido = _limpiar_html(entry.get("summary", entry.get("description", "")))
            fuente = _fuente_real(entry, url)
            fecha = _extraer_fecha(entry)

            items.append(ItemInformativo(
                id=f"rss-{len(items)}",
                titulo=titulo,
                fuente=fuente,
                contenido=contenido[:2000],
                url=link,
                fecha=fecha,
                tags=["rss", fuente.lower().replace(" ", "_")],
            ))
        except Exception as e:
            logger.warning(f"RSS error procesando entry en {url}: {e}")
            continue

    return items


def _leer_fuente_local(cfg: dict) -> list[ItemInformativo]:
    ruta = Path(cfg["ruta"])
    if not ruta.exists():
        logger.warning(f"Fuente local no encontrada: {ruta}")
        return []
    try:
        texto = ruta.read_text(encoding="utf-8")
        lineas = [l.strip() for l in texto.split("\n") if l.strip()]
        items = []
        for i, linea in enumerate(lineas):
            items.append(ItemInformativo(
                id=f"local-{i}",
                titulo=linea[:80],
                fuente=ruta.stem,
                contenido=linea,
                url="",
                fecha=datetime.fromtimestamp(ruta.stat().st_mtime, tz=timezone.utc),
                tags=["local", ruta.stem],
            ))
        logger.info(f"Fuente local {ruta.name}: {len(items)} líneas")
        return items
    except Exception as e:
        logger.error(f"Error leyendo fuente local {ruta}: {e}")
        return []


def obtener_items(limite: int = 20, usar_cache: bool = True) -> list[ItemInformativo]:
    cache_key = f"rss:{limite}"
    if usar_cache and cache_key in _CACHE:
        timestamp, resultados = _CACHE[cache_key]
        if time.time() - timestamp < CACHE_DURACION:
            logger.debug("RSS desde cache")
            return resultados

    config = _cargar_config()
    todos: list[ItemInformativo] = []

    for feed_cfg in _obtener_feeds_activos(config):
        items = _fetch_rss(feed_cfg["url"])
        logger.info(f"RSS {feed_cfg['url'].split('/')[2]}: {len(items)} items")
        for it in items:
            if any(f in it.fuente for f in _FUENTES_CHILENAS):
                todos.append(it)
            elif _RE_CHILE.search(it.titulo + " " + (it.contenido or "")):
                todos.append(it)

    for local_cfg in _obtener_fuentes_locales(config):
        items = _leer_fuente_local(local_cfg)
        todos.extend(items)

    if not todos:
        logger.warning("No se obtuvieron items de ninguna fuente")
        return []

    todos.sort(key=lambda x: x.fecha, reverse=True)

    vistos: set[str] = set()
    unicos: list[ItemInformativo] = []
    for it in todos:
        clave = it.url or it.titulo
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(it)
        if len(unicos) >= limite:
            break

    resultado = unicos[:limite]
    _CACHE[cache_key] = (time.time(), resultado)
    logger.info(f"RSS total: {len(resultado)} items únicos de {len(todos)} brutos")
    return resultado
