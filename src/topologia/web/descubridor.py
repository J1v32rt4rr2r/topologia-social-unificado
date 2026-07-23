from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import feedparser
import requests
import yaml

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo
from topologia.prompts import PromptLoader


RUTAS_RSS = [
    "/feed",
    "/feed/",
    "/rss",
    "/rss/",
    "/rss.xml",
    "/feed.xml",
    "/index.xml",
    "/?feed=rss2",
    "/?format=rss",
]

USER_AGENT = (
    "TopologiaSocial/2.0 "
    "(Proyecto de investigacion sociologica; "
    "monitoreo de clima cultural chileno; "
    "https://github.com/J1v32rt4rr2r/topologia-social-unificado; "
    "contacto: j1v32rt4rr2r@proton.me)"
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_TIMEOUT = 15
_CACHE: dict[str, tuple[float, list[ItemInformativo]]] = {}


def _limpiar(texto: str) -> str:
    return _WS_RE.sub(" ", _HTML_TAG_RE.sub(" ", texto)).strip()


def _cargar_fuentes_conocidas() -> list[str]:
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "feeds.yaml"
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    conocidas = []
    for feed in cfg.get("rss", []):
        url = feed.get("url", "")
        if url:
            conocidas.append(url.split("/")[2])
    for _, medio in cfg.get("espectro_b", {}).items():
        url = medio.get("url", "")
        if url:
            conocidas.append(url.split("/")[2])
    return sorted(set(conocidas))


def _generar_plan_borqueda(nodos_deficit: list[str], nodos_prioritarios: list[str]) -> list[dict]:
    prompt_loader = PromptLoader()
    contexto_nodos = ""
    try:
        ruta_nodos = Path(__file__).resolve().parent.parent.parent.parent / "config" / "nodos.yaml"
        with ruta_nodos.open(encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        for n in cfg.get("nodos", []):
            nid = n.get("id", "")
            if nid in nodos_deficit or nid in nodos_prioritarios:
                contexto_nodos += f"- {nid}: {n.get('descripcion', n.get('m_desc', ''))}\n"
    except Exception:
        contexto_nodos = ", ".join(nodos_deficit + nodos_prioritarios)

    fuentes_conocidas = _cargar_fuentes_conocidas()
    prompt = prompt_loader.load("descubridor_fuentes",
        contexto_nodos=contexto_nodos or "Sin descripción disponible.",
        nodos_deficit=", ".join(nodos_deficit) if nodos_deficit else "Ninguno",
        fuentes_conocidas=", ".join(fuentes_conocidas[:15]),
    )

    try:
        from topologia.models.llm import LLMClient
        import json
        llm = LLMClient()
        raw = llm.generar_json(prompt, temperatura=0.4, max_tokens=1024)
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
        consultas = data.get("consultas", [])
        sitios = data.get("sitios_sugeridos", [])
        logger.info(f"Descubridor: LLM sugirió {len(consultas)} consultas y {len(sitios)} sitios")
        return consultas + sitios
    except Exception as e:
        logger.warning(f"Error generando plan de búsqueda: {e}")
        return []


def _descubrir_rss_en_sitio(dominio: str) -> list[str]:
    encontrados: list[str] = []
    base = f"https://{dominio}"
    for ruta in RUTAS_RSS:
        url = base + ruta
        try:
            resp = requests.head(url, timeout=_TIMEOUT, headers={"User-Agent": USER_AGENT}, allow_redirects=True)
            ct = resp.headers.get("content-type", "")
            if resp.status_code == 200 and ("xml" in ct or "rss" in ct or "atom" in ct or "+xml" in ct):
                encontrados.append(url)
                logger.info(f"  RSS descubierto: {url}")
                if len(encontrados) >= 2:
                    break
                continue
            if resp.status_code == 200:
                resp2 = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": USER_AGENT})
                texto = resp2.text[:500].lower()
                if "<?xml" in texto or "<rss" in texto or "<feed" in texto or "<rdf" in texto:
                    encontrados.append(url)
                    logger.info(f"  RSS descubierto (por contenido): {url}")
                    if len(encontrados) >= 2:
                        break
        except Exception:
            continue
    return encontrados


def _fetch_rss(url: str) -> list[ItemInformativo]:
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
    except Exception as e:
        logger.debug(f"  Error fetching {url}: {e}")
        return []

    items: list[ItemInformativo] = []
    vistos: set[str] = set()
    for entry in feed.entries:
        try:
            link = entry.get("link", "")
            if not link or link in vistos:
                continue
            vistos.add(link)
            titulo = _limpiar(entry.get("title", ""))
            contenido = _limpiar(entry.get("summary", entry.get("description", "")))
            fecha = datetime.now()
            for campo in ("published_parsed", "updated_parsed"):
                parsed = entry.get(campo)
                if parsed:
                    try:
                        from time import mktime
                        fecha = datetime.fromtimestamp(mktime(parsed))
                    except Exception:
                        pass
                    break
            items.append(ItemInformativo(
                id=f"descubierto-{len(items)}",
                titulo=titulo,
                fuente=url.split("/")[2],
                contenido=contenido[:2000],
                url=link,
                fecha=fecha,
                tags=["descubierto", url.split("/")[2]],
            ))
        except Exception:
            continue
    return items


def buscar_nuevas_fuentes(
    nodos_deficit: list[str],
    nodos_prioritarios: list[str] | None = None,
    max_por_nodo: int = 3,
) -> list[ItemInformativo]:
    if not nodos_deficit:
        logger.info("Descubridor: sin nodos con déficit, se omite")
        return []

    logger.info(f"Descubridor: buscando fuentes para nodos con déficit: {nodos_deficit}")

    plan = _generar_plan_borqueda(nodos_deficit, nodos_prioritarios or [])
    if not plan:
        logger.warning("Descubridor: no se generó plan de búsqueda")
        return []

    dominios_a_probar: list[str] = []
    for entry in plan:
        if isinstance(entry, dict):
            url = entry.get("url", "")
            if url:
                dominio = url.split("/")[2] if "://" in url else url
                dominios_a_probar.append(dominio)
        elif isinstance(entry, str):
            dominios_a_probar.append(entry)

    descubiertos: list[str] = []
    total = 0
    for dominio in sorted(set(dominios_a_probar)):
        if dominio in _cargar_fuentes_conocidas():
            continue
        feeds = _descubrir_rss_en_sitio(dominio)
        for feed_url in feeds:
            if feed_url not in descubiertos:
                descubiertos.append(feed_url)

    if not descubiertos:
        logger.warning("Descubridor: no se encontraron RSS en los sitios sugeridos")
        return []

    logger.info(f"Descubridor: {len(descubiertos)} feeds nuevos encontrados")
    todos: list[ItemInformativo] = []
    for feed_url in descubiertos:
        items = _fetch_rss(feed_url)
        logger.info(f"  {feed_url}: {len(items)} items")
        todos.extend(items)
        total += len(items)

    logger.info(f"Descubridor: {total} items obtenidos de {len(descubiertos)} fuentes nuevas")
    return todos


def buscar_para_brechas(
    brechas: dict[str, int],
    nodos_prioritarios: list[str] | None = None,
) -> list[ItemInformativo]:
    nodos_deficit = [n for n, c in brechas.items() if c == 0]
    return buscar_nuevas_fuentes(nodos_deficit, nodos_prioritarios)
