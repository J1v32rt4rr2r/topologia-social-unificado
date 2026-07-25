from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo


USER_AGENT = (
    "TopologiaSocial/3.0 "
    "(Proyecto de investigacion sociologica; "
    "monitoreo de clima cultural chileno; "
    "contacto: j1v32rt4rr2r@proton.me)"
)
TIMEOUT = 60
DELAY_ENTRE_PETICIONES = 1.0
MAX_SNAPSHOTS_POR_FUENTE = 300
ITEMS_POR_FUENTE = 30
MAX_TOTAL = 200

_RE_FECHA_URL = re.compile(r"/(\d{4})/(\d{2})(?:/(\d{2}))?/")

_ultima_peticion: float = 0.0

# ─── Cache ─────────────────────────────────────────────────────────────────


def _ruta_raw() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "historico" / "raw"


def _ruta_cache(dominio: str, timestamp: str) -> Path:
    ruta = _ruta_raw() / dominio
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta / f"{timestamp}.html"


def _en_cache(dominio: str, timestamp: str) -> bool:
    return _ruta_cache(dominio, timestamp).exists()


# ─── Wayback CDX API ───────────────────────────────────────────────────────


def _esperar_rate_limit():
    global _ultima_peticion
    ahora = time.time()
    diff = ahora - _ultima_peticion
    if diff < DELAY_ENTRE_PETICIONES:
        time.sleep(DELAY_ENTRE_PETICIONES - diff)
    _ultima_peticion = time.time()


def _request_with_retry(url: str, max_retries: int = 3, **kwargs) -> requests.Response | None:
    """Wrapper con retry exponencial + rate limiting."""
    for intento in range(max_retries + 1):
        _esperar_rate_limit()
        try:
            resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, **kwargs)
            if resp.status_code == 429:
                wait = 10 * (2 ** intento)
                logger.warning(f"HTTP 429, esperando {wait}s (intento {intento+1}/{max_retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if intento < max_retries:
                wait = 5 * (2 ** intento)
                logger.warning(f"Request error (intento {intento+1}/{max_retries}): {e}. Esperando {wait}s")
                time.sleep(wait)
            else:
                logger.warning(f"Request falló tras {max_retries} reintentos: {e}")
                return None
    return None


def _urls_a_evitar() -> list[re.Pattern]:
    return [
        re.compile(r"/tag/", re.I),
        re.compile(r"/category/", re.I),
        re.compile(r"/author/", re.I),
        re.compile(r"/page/\d+", re.I),
        re.compile(r"/wp-", re.I),
        re.compile(r"/feed", re.I),
        re.compile(r"/comments", re.I),
        re.compile(r"#respond", re.I),
        re.compile(r"/\?s=", re.I),
        re.compile(r"/\?p=", re.I),
    ]


def _es_url_valida(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path or path == "":
        return False
    for patron in _urls_a_evitar():
        if patron.search(url):
            return False
    return True


def buscar_snapshots(
    dominio: str,
    desde: str,
    hasta: str,
    max_snapshots: int = 500,
    url_pattern: str | None = None,
) -> list[dict]:
    """Consulta Wayback CDX API y retorna snapshots (status=200, text/html).

    Si url_pattern es None, usa '{dominio}/*'. Para filtrar por año del
    periodo usa '{dominio}/{año}/*' (mucho más rápido y preciso).
    """
    if url_pattern is None:
        url_pattern = f"{dominio}/*"
    url = "https://web.archive.org/cdx/search/cdx"
    params = {
        "url": url_pattern,
        "from": desde,
        "to": hasta,
        "output": "json",
        "limit": str(max_snapshots),
        "fl": "timestamp,original,statuscode,mimetype",
        "collapse": "urlkey",
        "filter": "statuscode:200",
    }

    resp = _request_with_retry(url, params=params)
    if resp is None:
        logger.warning(f"CDX error para {dominio} ({desde}-{hasta}): sin respuesta tras reintentos")
        return []
    try:
        data = resp.json()
    except Exception as e:
        logger.warning(f"CDX error parseando JSON para {dominio}: {e}")
        return []

    if not data or len(data) < 2:
        logger.info(f"CDX sin resultados para {dominio}")
        return []

    snapshots = []
    for row in data[1:]:
        if len(row) >= 4:
            ts, orig, code, mime = row[0], row[1], row[2], row[3]
            if mime and "html" in mime and _es_url_valida(orig):
                snapshots.append({
                    "timestamp": ts,
                    "original": orig,
                    "statuscode": code,
                    "mimetype": mime,
                })

    logger.info(f"CDX {dominio}: {len(snapshots)} snapshots válidos de {len(data)-1} totales")
    return snapshots


# ─── Descarga de snapshots ─────────────────────────────────────────────────


def _extraer_titulo(soup: BeautifulSoup) -> str:
    titulo = soup.title.string if soup.title else ""
    if titulo:
        titulo = re.sub(r"\s+", " ", titulo).strip()
        titulo = re.sub(r"\s*[|–-]\s*.*$", "", titulo).strip()
    return titulo or ""


def _extraer_contenido(soup: BeautifulSoup, selector: str) -> str:
    if selector:
        for sel in selector.split(","):
            sel = sel.strip()
            if not sel:
                continue
            elementos = soup.select(sel)
            if elementos:
                texto = " ".join(e.get_text(strip=True) for e in elementos)
                texto = re.sub(r"\s+", " ", texto).strip()
                if len(texto) > 100:
                    return texto[:3000]

    texto = soup.get_text(separator=" ", strip=True)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:2000]


def descargar_snapshot(
    timestamp: str,
    url_original: str,
    selector: str = "",
) -> dict | None:
    """Descarga un snapshot de Wayback Machine y extrae título + contenido.

    Returns dict con keys: titulo, contenido, url_archivada, timestamp
    o None si falla.
    """
    dominio = urlparse(url_original).hostname or "unknown"

    if _en_cache(dominio, timestamp):
        html = _ruta_cache(dominio, timestamp).read_text(encoding="utf-8", errors="replace")
    else:
        archived_url = f"https://web.archive.org/web/{timestamp}/{url_original}"
        resp = _request_with_retry(archived_url, allow_redirects=True)
        if resp is None:
            return None
        html = resp.text
        try:
            _ruta_cache(dominio, timestamp).write_text(html, encoding="utf-8")
        except OSError:
            pass

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return None

    return {
        "titulo": _extraer_titulo(soup),
        "contenido": _extraer_contenido(soup, selector),
        "url_archivada": f"https://web.archive.org/web/{timestamp}/{url_original}",
        "timestamp": timestamp,
    }


# ─── Muestreo temporal ─────────────────────────────────────────────────────


def _samplear_snapshots(snapshots: list[dict], n: int) -> list[dict]:
    """Samplea N snapshots distribuidos uniformemente en el rango temporal."""
    if len(snapshots) <= n:
        return snapshots
    snapshots = sorted(snapshots, key=lambda s: s["timestamp"])
    indices = [int(i * (len(snapshots) - 1) / (n - 1)) for i in range(n)]
    return [snapshots[i] for i in indices]


# ─── Recolección por periodo ────────────────────────────────────────────────


def _extraer_fecha_url(url: str) -> str | None:
    """Extrae fecha YYYY-MM-DD desde URL tipo /YYYY/MM/DD/. Retorna None si no hay fecha."""
    m = _RE_FECHA_URL.search(url)
    if m:
        y, mo, d = m.group(1), m.group(2), m.group(3)
        if d:
            return f"{y}-{mo}-{d}"
        return f"{y}-{mo}-01"
    return None


def _filtrar_snapshots_por_periodo(
    snapshots: list[dict],
    fecha_inicio: str,
    fecha_fin: str,
    buffer_dias: int = 30,
) -> list[dict]:
    """Filtra snapshots: solo conserva URLs cuya fecha de publicación (en URL)
    caiga dentro del periodo ± buffer. URLs sin fecha se conservan también.
    """
    inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
    inicio_buf = inicio - timedelta(days=buffer_dias)
    fin_buf = fin + timedelta(days=buffer_dias)

    filtrados = []
    descartados = 0
    con_fecha = 0
    sin_fecha = 0

    for s in snapshots:
        url = s["original"]
        fecha_url = _extraer_fecha_url(url)
        if fecha_url:
            con_fecha += 1
            try:
                f = datetime.strptime(fecha_url, "%Y-%m-%d")
                if inicio_buf <= f <= fin_buf:
                    filtrados.append(s)
                else:
                    descartados += 1
            except ValueError:
                filtrados.append(s)
        else:
            sin_fecha += 1
            filtrados.append(s)

    logger.info(
        f"Filtro fecha URL: {con_fecha} con fecha, {sin_fecha} sin fecha, "
        f"{descartados} descartados fuera del periodo ±{buffer_dias}d"
    )
    return filtrados


def _cargar_items_desde_cache(
    dominio: str,
    periodo_id: str,
    fecha_inicio: str,
    fecha_fin: str,
    buffer_dias: int = 30,
    selector: str = "article",
    max_items: int = 50,
) -> list[ItemInformativo]:
    """Carga items desde archivos HTML cacheados en disco.

    Escanea data/historico/raw/{dominio}/*.html (y www.{dominio}),
    verifica que el timestamp esté dentro del periodo ± buffer, y parsea.
    """
    candidatos = [dominio]
    if dominio.startswith("www."):
        candidatos.append(dominio[4:])
    else:
        candidatos.append(f"www.{dominio}")

    archivos: list[Path] = []
    for d in candidatos:
        ruta = _ruta_raw() / d
        if ruta.exists():
            archivos.extend(sorted(ruta.glob("*.html")))

    inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d") - timedelta(days=buffer_dias)
    fin = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=buffer_dias)
    items: list[ItemInformativo] = []
    vistos_url: set[str] = set()

    for archivo in archivos:
        if len(items) >= max_items:
            break
        ts = archivo.stem
        try:
            ts_dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
        except ValueError:
            continue
        if not (inicio <= ts_dt <= fin):
            continue

        html = archivo.read_text(encoding="utf-8", errors="replace")
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            continue

        titulo = _extraer_titulo(soup)
        contenido = _extraer_contenido(soup, selector)
        if len(contenido) < 50:
            continue
        if contenido in vistos_url:
            continue
        vistos_url.add(contenido)

        item = ItemInformativo(
            id=f"hist-{periodo_id}-cache-{len(items)}",
            titulo=(titulo or archivo.stem)[:200],
            fuente=f"wayback:{dominio}",
            contenido=contenido,
            url=f"https://web.archive.org/web/{ts}/https://{dominio}",
            tags=["historico", periodo_id, dominio.replace(".", "_"), "cache"],
        )
        items.append(item)

    if items:
        logger.info(f"[{periodo_id}] Cache {dominio}: {len(items)} items cargados")
    return items


def _items_url_cache(dominio: str) -> set[str]:
    """Retorna conjunto de timestamps cacheados para el dominio (incluye www y no-www)."""
    candidatos = [dominio]
    if dominio.startswith("www."):
        candidatos.append(dominio[4:])
    else:
        candidatos.append(f"www.{dominio}")
    cached: set[str] = set()
    for d in candidatos:
        ruta = _ruta_raw() / d
        if ruta.exists():
            for archivo in ruta.glob("*.html"):
                cached.add(archivo.stem)
    return cached


def recolectar_items_para_periodo(
    periodo: dict,
    items_por_fuente: int = 30,
    max_items_total: int = 200,
    solo_cache: bool = False,
) -> list[ItemInformativo]:
    """Orquesta recolección para un periodo histórico completo.

    Para cada fuente definida en el periodo:
      1. Carga items desde cache local primero (offline, instantáneo)
      2. Si faltan items, consulta CDX → snapshots
      3. Descarga solo los snapshots no cacheados
      4. Extrae título + contenido → ItemInformativo
    """
    desde = periodo["fecha_inicio"].replace("-", "")
    hasta = periodo["fecha_fin"].replace("-", "")
    items_totales: list[ItemInformativo] = []
    vistos_urls: set[str] = set()

    d_inicio = datetime.strptime(periodo["fecha_inicio"], "%Y-%m-%d")
    d_fin = datetime.strptime(periodo["fecha_fin"], "%Y-%m-%d")
    anios_periodo = {str(a) for a in range(d_inicio.year, d_fin.year + 1)}

    for fuente in periodo.get("fuentes", []):
        dominio = fuente["dominio"]
        selector = fuente.get("selector_articulo", "article")

        if len(items_totales) >= max_items_total:
            break

        # Fase 1: cargar desde cache local
        items_cache = _cargar_items_desde_cache(
            dominio, periodo["id"],
            periodo["fecha_inicio"], periodo["fecha_fin"],
            selector=selector,
            max_items=items_por_fuente,
        )
        for it in items_cache:
            if len(items_totales) >= max_items_total:
                break
            if it.contenido not in vistos_urls:
                vistos_urls.add(it.contenido)
                items_totales.append(it)

        if len(items_totales) >= max_items_total:
            break

        if len(items_cache) >= items_por_fuente:
            continue

        # Fase 2: consultar CDX (solo si no estamos en modo solo_cache)
        if solo_cache:
            continue

        snapshots = []
        for anio in sorted(anios_periodo):
            logger.info(f"[{periodo['id']}] CDX: {dominio}/{anio} ({desde}-{hasta})")
            parte = buscar_snapshots(dominio, desde, hasta,
                                     url_pattern=f"{dominio}/{anio}/*")
            snapshots.extend(parte)

        if not snapshots:
            logger.info(f"[{periodo['id']}] Fallback CDX global: {dominio} ({desde}-{hasta})")
            snapshots = buscar_snapshots(dominio, desde, hasta)

        if not snapshots:
            logger.info(f"[{periodo['id']}][CDX] Sin snapshots para {dominio}")
            continue

        snapshots = _filtrar_snapshots_por_periodo(
            snapshots, periodo["fecha_inicio"], periodo["fecha_fin"]
        )
        if not snapshots:
            logger.info(f"[{periodo['id']}] Sin snapshots tras filtro de fecha para {dominio}")
            continue

        # Priorizar snapshots cacheados (False → True en sort)
        cached_ts = _items_url_cache(dominio)
        snapshots.sort(key=lambda s: s["timestamp"] not in cached_ts)

        restantes = items_por_fuente - len(items_cache)
        muestras = _samplear_snapshots(snapshots, min(restantes, len(snapshots)))
        logger.info(
            f"[{periodo['id']}] {dominio}: {len(snapshots)} snapshots → "
            f"{len(muestras)} muestras ({len(items_cache)} desde cache)"
        )

        for snap in muestras:
            if len(items_totales) >= max_items_total:
                break
            ts = snap["timestamp"]
            url = snap["original"]

            if url in vistos_urls:
                continue
            vistos_urls.add(url)

            resultado = descargar_snapshot(ts, url, selector)
            if not resultado:
                continue

            titulo = resultado["titulo"] or url.split("/")[-1][:80]
            contenido = resultado["contenido"]
            if len(contenido) < 50:
                continue

            item = ItemInformativo(
                id=f"hist-{periodo['id']}-{len(items_totales)}",
                titulo=titulo[:200],
                fuente=f"wayback:{dominio}",
                contenido=contenido,
                url=resultado["url_archivada"],
                tags=["historico", periodo["id"], dominio.replace(".", "_")],
            )
            items_totales.append(item)

    logger.info(
        f"[{periodo['id']}] Recolección completada: {len(items_totales)} items "
        f"de {len(periodo.get('fuentes', []))} fuentes"
    )
    return items_totales
