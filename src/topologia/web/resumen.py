from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo


SECCIONES = [
    "nacional",
]

URL_BASE = "https://resumen.cl"
TIMEOUT_MS = 20000
_WS_RE = re.compile(r"\s+")
_HTML_CLEAN_RE = re.compile(r"<[^>]+>")


def _limpiar(texto: str) -> str:
    texto = _HTML_CLEAN_RE.sub(" ", texto)
    texto = _WS_RE.sub(" ", texto).strip()
    return texto


def _scrapear_seccion(
    browser: Any, seccion: str, timeout: int = TIMEOUT_MS
) -> list[dict[str, str]]:
    url = f"{URL_BASE}/seccion/{seccion}"
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    articulos: list[dict[str, str]] = []
    try:
        page.goto(url, wait_until="networkidle", timeout=timeout)
        page.wait_for_timeout(2000)

        contenedores = page.query_selector_all(".rsmn-seccion")
        for c in contenedores:
            link_el = c.query_selector(".rsmn-seccion__info-link")
            if not link_el:
                continue
            href = link_el.get_attribute("href") or ""
            if not href or href.startswith("#"):
                continue
            titulo = _limpiar(link_el.inner_text())
            if not titulo or len(titulo) < 15:
                continue
            full_url = href if href.startswith("http") else f"{URL_BASE}{href}"

            extracto = ""
            info_el = c.query_selector(".rsmn-seccion__info")
            if info_el:
                raw = info_el.inner_text()
                sin_titulo = raw.replace(titulo, "", 1).strip()
                extracto = _limpiar(sin_titulo)[:500]

            articulos.append({
                "titulo": titulo,
                "url": full_url,
                "extracto": extracto,
            })
    except Exception as e:
        logger.warning(f"Resumen.cl error en sección '{seccion}': {e}")
    finally:
        page.close()

    return articulos


def _lanzar_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("playwright no está instalado. Ejecute: pip install playwright && playwright install chromium")
        return None
    try:
        p = sync_playwright().start()
        browser = p.chromium.launch(headless=True)
        return browser, p
    except Exception as e:
        logger.error(f"Resumen.cl: no se pudo iniciar Chromium: {e}")
        return None


def obtener_items(limite: int = 10) -> list[ItemInformativo]:
    resultado = _lanzar_browser()
    if resultado is None:
        return []
    browser, playwright = resultado

    items: list[ItemInformativo] = []
    vistos: set[str] = set()
    try:
        for seccion in SECCIONES:
            if len(items) >= limite:
                break
            articulos = _scrapear_seccion(browser, seccion)
            for a in articulos:
                if len(items) >= limite:
                    break
                if a["url"] in vistos:
                    continue
                vistos.add(a["url"])
                contenido = a["extracto"] or a["titulo"]
                items.append(ItemInformativo(
                    id=f"resumen-{len(items)}",
                    titulo=a["titulo"],
                    fuente="resumen.cl",
                    contenido=contenido,
                    url=a["url"],
                    fecha=datetime.now(timezone.utc),
                    tags=["rss", "resumen.cl", seccion],
                ))
    finally:
        try:
            browser.close()
        except Exception:
            pass
        try:
            playwright.stop()
        except Exception:
            pass

    logger.info(f"Resumen.cl: {len(items)} items extraídos (máx {limite})")
    return items


if __name__ == "__main__":
    import json
    items = obtener_items(limite=5)
    print(json.dumps([it.model_dump() for it in items], indent=2, default=str))
