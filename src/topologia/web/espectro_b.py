"""
Fase 2 — Espectro B: scrapers Playwright para medios mainstream chilenos
que bloquean RSS. Cada medio tiene su propia estructura HTML.

Medios cubiertos:
  - Emol (emol.com)
  - La Tercera (latercera.com)
  - BioBioChile (biobiochile.cl)
  - Canal 13 (canal13.cl)
  - TVN (tvn.cl / 24horas.cl)
  - Meganoticias (meganoticias.cl)

La identificación como proyecto de investigación sociológica se incluye
en el User-Agent y headers HTTP para transparencia.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo


USER_AGENT = (
    "TopologiaSocial/2.0 "
    "(Proyecto de investigacion sociologica; "
    "monitoreo de clima cultural chileno; "
    "https://github.com/J1v32rt4rr2r/topologia-social-unificado; "
    "contacto: j1v32rt4rr2r@proton.me)"
)

TIMEOUT_MS = 30000
_DELAY = 2.0  # 2 segundos entre scrapers
_ultimo_acceso: float = 0.0


def _esperar() -> None:
    global _ultimo_acceso
    ahora = time.time()
    diff = ahora - _ultimo_acceso
    if diff < _DELAY:
        time.sleep(_DELAY - diff)
    _ultimo_acceso = time.time()


def _lanzar_navegador():
    """Inicia Chromium via Playwright con configuración chilena."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("playwright no instalado: pip install playwright && playwright install chromium")
        return None
    try:
        p = sync_playwright().start()
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="es-CL",
            timezone_id="America/Santiago",
        )
        context.set_extra_http_headers({
            "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
            "From": "j1v32rt4rr2r@proton.me",
        })
        return browser, context, p
    except Exception as e:
        logger.error(f"Espectro B: no se pudo iniciar Chromium: {e}")
        return None


def _cerrar_navegador(browser, playwright) -> None:
    try:
        browser.close()
    except Exception:
        pass
    try:
        playwright.stop()
    except Exception:
        pass


# --- Scrapers individuales ---

def _scrape_emol(context: Any) -> list[dict]:
    """Extrae titulares de la portada de Emol."""
    page = context.new_page()
    articulos = []
    try:
        page.goto("https://www.emol.com", wait_until="networkidle", timeout=TIMEOUT_MS)
        page.wait_for_timeout(2000)
        enlaces = page.query_selector_all("a[href*='/noticias/']")
        vistos = set()
        for el in enlaces:
            href = el.get_attribute("href") or ""
            titulo = el.inner_text().strip()
            if not titulo or len(titulo) < 20 or href in vistos:
                continue
            vistos.add(href)
            full_url = href if href.startswith("http") else f"https://www.emol.com{href}"
            articulos.append({"titulo": titulo, "url": full_url, "extracto": ""})
    except Exception as e:
        logger.warning(f"Emol error: {e}")
    finally:
        page.close()
    return articulos


def _scrape_latercera(context: Any) -> list[dict]:
    """Extrae titulares de la portada de La Tercera."""
    page = context.new_page()
    articulos = []
    try:
        page.goto("https://www.latercera.com", wait_until="networkidle", timeout=TIMEOUT_MS)
        page.wait_for_timeout(2000)
        enlaces = page.query_selector_all("article a[href]")
        vistos = set()
        for el in enlaces:
            href = el.get_attribute("href") or ""
            titulo = el.inner_text().strip()
            if not titulo or len(titulo) < 20 or href in vistos:
                continue
            vistos.add(href)
            full_url = href if href.startswith("http") else f"https://www.latercera.com{href}"
            articulos.append({"titulo": titulo, "url": full_url, "extracto": ""})
    except Exception as e:
        logger.warning(f"La Tercera error: {e}")
    finally:
        page.close()
    return articulos


def _scrape_biobio(context: Any) -> list[dict]:
    """Extrae titulares de BioBioChile."""
    page = context.new_page()
    articulos = []
    try:
        page.goto("https://www.biobiochile.cl", wait_until="networkidle", timeout=TIMEOUT_MS)
        page.wait_for_timeout(2000)
        enlaces = page.query_selector_all("a[href*='/noticias/']")
        vistos = set()
        for el in enlaces:
            href = el.get_attribute("href") or ""
            titulo = el.inner_text().strip()
            if not titulo or len(titulo) < 15 or href in vistos:
                continue
            vistos.add(href)
            full_url = href if href.startswith("http") else f"https://www.biobiochile.cl{href}"
            articulos.append({"titulo": titulo, "url": full_url, "extracto": ""})
    except Exception as e:
        logger.warning(f"BioBio error: {e}")
    finally:
        page.close()
    return articulos


def _scrape_canal13(context: Any) -> list[dict]:
    """Extrae titulares de Canal 13."""
    page = context.new_page()
    articulos = []
    try:
        page.goto("https://www.canal13.cl", wait_until="networkidle", timeout=TIMEOUT_MS)
        page.wait_for_timeout(2000)
        enlaces = page.query_selector_all("a[href*='/noticias/']")
        vistos = set()
        for el in enlaces:
            href = el.get_attribute("href") or ""
            titulo = el.inner_text().strip()
            if not titulo or len(titulo) < 15 or href in vistos:
                continue
            vistos.add(href)
            full_url = href if href.startswith("http") else f"https://www.canal13.cl{href}"
            articulos.append({"titulo": titulo, "url": full_url, "extracto": ""})
    except Exception as e:
        logger.warning(f"Canal 13 error: {e}")
    finally:
        page.close()
    return articulos


def _scrape_tvn(context: Any) -> list[dict]:
    """Extrae titulares de 24 Horas (TVN)."""
    page = context.new_page()
    articulos = []
    try:
        page.goto("https://www.24horas.cl", wait_until="networkidle", timeout=TIMEOUT_MS)
        page.wait_for_timeout(2000)
        enlaces = page.query_selector_all("a[href*='/noticias/']")
        vistos = set()
        for el in enlaces:
            href = el.get_attribute("href") or ""
            titulo = el.inner_text().strip()
            if not titulo or len(titulo) < 15 or href in vistos:
                continue
            vistos.add(href)
            full_url = href if href.startswith("http") else f"https://www.24horas.cl{href}"
            articulos.append({"titulo": titulo, "url": full_url, "extracto": ""})
    except Exception as e:
        logger.warning(f"TVN error: {e}")
    finally:
        page.close()
    return articulos


def _scrape_meganoticias(context: Any) -> list[dict]:
    """Extrae titulares de Meganoticias."""
    page = context.new_page()
    articulos = []
    try:
        page.goto("https://www.meganoticias.cl", wait_until="networkidle", timeout=TIMEOUT_MS)
        page.wait_for_timeout(2000)
        enlaces = page.query_selector_all("a[href*='/noticias/']")
        vistos = set()
        for el in enlaces:
            href = el.get_attribute("href") or ""
            titulo = el.inner_text().strip()
            if not titulo or len(titulo) < 15 or href in vistos:
                continue
            vistos.add(href)
            full_url = href if href.startswith("http") else f"https://www.meganoticias.cl{href}"
            articulos.append({"titulo": titulo, "url": full_url, "extracto": ""})
    except Exception as e:
        logger.warning(f"Meganoticias error: {e}")
    finally:
        page.close()
    return articulos


# --- Registro de scrapers ---

SCRAPERS: list[tuple[str, str, Callable]] = [
    ("emol",         "Espectro B/Emol",         _scrape_emol),
    ("latercera",    "Espectro B/La Tercera",   _scrape_latercera),
    ("biobio",       "Espectro B/BioBio",       _scrape_biobio),
    ("canal13",      "Espectro B/Canal 13",     _scrape_canal13),
    ("tvn",          "Espectro B/TVN",          _scrape_tvn),
    ("meganoticias", "Espectro B/Meganoticias", _scrape_meganoticias),
]


def obtener_items(limite_por_medio: int = 5) -> list[ItemInformativo]:
    """
    Ejecuta todos los scrapers del Espectro B secuencialmente.

    Args:
        limite_por_medio: Máximo de artículos por medio (default 5).

    Returns:
        Lista combinada de ItemInformativo de todos los medios.
    """
    resultado = _lanzar_navegador()
    if resultado is None:
        return []
    browser, context, playwright = resultado

    todos: list[ItemInformativo] = []
    try:
        for medio_id, nombre_fuente, scraper_fn in SCRAPERS:
            _esperar()
            try:
                articulos = scraper_fn(context)
            except Exception as e:
                logger.warning(f"{nombre_fuente} error inesperado: {e}")
                continue

            for i, a in enumerate(articulos[:limite_por_medio]):
                contenido = a["extracto"] or a["titulo"]
                todos.append(ItemInformativo(
                    id=f"eb-{medio_id}-{i}",
                    titulo=a["titulo"],
                    fuente=nombre_fuente,
                    contenido=contenido,
                    url=a["url"],
                    fecha=datetime.now(timezone.utc),
                    tags=["espectro-b", medio_id],
                ))
            logger.info(f"{nombre_fuente}: {len(articulos[:limite_por_medio])} items")

    finally:
        try:
            context.close()
        except Exception:
            pass
        _cerrar_navegador(browser, playwright)

    logger.info(f"Espectro B total: {len(todos)} items de {len(SCRAPERS)} medios")
    return todos
