"""Banco Central de Chile — Indicadores diarios oficiales.

Dos vías de acceso:

1. API BDE oficial (recomendada): https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx
   Requiere token de cuenta registrada (variable de entorno BCENTRAL_TOKEN).
   Consulta las series configuradas en SERIES_BDE (diarias: UF, dólar, IVP,
   TPM, euro) y SERIES_BDE_PERIODICAS (IMACEC, PIB, IPC) y usa la fecha real
   de cada observación (no 'now()').

2. Página pública de indicadores diarios (fallback sin token):
   https://si3.bcentral.cl/Indicadoressiete/secure/indicadoresdiarios.aspx
   La tabla (UF, IVP, dólar, IPC, TPM, cobre, etc.) se renderiza en el
   servidor con la fecha del día seleccionado. Los valores 'ND' (no
   disponibles, p. ej. fines de semana) se omiten.
"""

from __future__ import annotations

import html
import json
import os
import re
import time
from datetime import datetime, timezone

import requests

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo


USER_AGENT = (
    "TopologiaSocial/2.0 "
    "(Proyecto de investigacion sociologica; "
    "monitoreo de clima cultural chileno; "
    "https://github.com/J1v32rt4rr2r/topologia-social-unificado; "
    "contacto: j1v32rt4rr2r@proton.me)"
)
URL = "https://si3.bcentral.cl/Indicadoressiete/secure/indicadoresdiarios.aspx"
TIMEOUT = 20
CACHE_DURACION = 300

_CACHE: dict[str, tuple[float, list[ItemInformativo]]] = {}

_MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
}

_RE_SERIE = re.compile(r'<label[^>]*id="lblSerie(\d+)_(\d+)"[^>]*>(.*?)</label>', re.DOTALL)
_RE_VALOR = re.compile(r'<label[^>]*id="lblValor(\d+)_(\d+)"[^>]*>(.*?)</label>', re.DOTALL)
_RE_TXT_DATE = re.compile(r'name="txtDate"[^>]*value="([^"]+)"', re.DOTALL)


def _limpiar(texto: str) -> str:
    texto = re.sub(r"<script[^>]*>.*?</script>", "", texto, flags=re.DOTALL)
    texto = re.sub(r"<style[^>]*>.*?</style>", "", texto, flags=re.DOTALL)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def _parsear_fecha_selector(valor: str) -> datetime | None:
    """'02 Ago 2026' -> datetime (meses en español)."""
    partes = valor.strip().split()
    if len(partes) != 3:
        return None
    dia, mes, anio = partes
    if mes.lower() not in _MESES:
        return None
    try:
        return datetime(int(anio), _MESES[mes.lower()], int(dia), tzinfo=timezone.utc)
    except ValueError:
        return None


def _es_valor_valido(valor: str) -> bool:
    limpio = valor.strip().lower()
    return bool(limpio) and limpio not in {"nd", "&nbsp;", "-"}


def obtener_items(limite: int = 20) -> list[ItemInformativo]:
    cache_key = f"bcentral:{limite}"
    if cache_key in _CACHE:
        timestamp, resultados = _CACHE[cache_key]
        if time.time() - timestamp < CACHE_DURACION:
            return resultados

    items: list[ItemInformativo] = []
    try:
        resp = requests.get(URL, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        resp.encoding = "iso-8859-1"
        pagina = resp.text
    except requests.RequestException as e:
        logger.warning(f"BCentral error fetching {URL}: {e}")
        return []

    match_date = _RE_TXT_DATE.search(pagina)
    fecha = (
        _parsear_fecha_selector(match_date.group(1))
        if match_date
        else None
    )
    if fecha is None:
        fecha = datetime.now(timezone.utc)

    series: dict[tuple[str, str], str] = {
        (m.group(1), m.group(2)): _limpiar(m.group(3))
        for m in _RE_SERIE.finditer(pagina)
    }
    valores: dict[tuple[str, str], str] = {
        (m.group(1), m.group(2)): _limpiar(m.group(3))
        for m in _RE_VALOR.finditer(pagina)
    }

    for clave, nombre in series.items():
        valor = valores.get(clave, "")
        if not _es_valor_valido(valor):
            continue
        items.append(ItemInformativo(
            id=f"bcentral-{len(items)}",
            titulo=f"{nombre}: {valor}",
            fuente="bcentral",
            contenido=(
                f"Indicador oficial del Banco Central de Chile al "
                f"{fecha.strftime('%d/%m/%Y')}: {nombre} = {valor}."
            ),
            url=URL,
            fecha=fecha,
            tags=["bcentral", "economia"],
            nodo_sugerido="ECONOMIA",
        ))

    _CACHE[cache_key] = (time.time(), items)
    logger.info(f"BCentral: {len(items)} indicadores al {fecha.strftime('%d/%m/%Y')}")
    return items[:limite]


# ---------------------------------------------------------------------------
# API BDE oficial (Banco Central de Chile)
# Requiere token de acceso (cuenta registrada en si3.bcentral.cl/Siete/es/Siete/API).
# Si no hay token configurado, se usa el scraping de la página pública.
# ---------------------------------------------------------------------------

URL_API = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"

#: Códigos de series BDE de interés para el nodo ECONOMIA.
#: Descubiertos vía SearchSeries(frequency=DAILY) del catálogo oficial.
SERIES_BDE: dict[str, str] = {
    "Unidad de fomento (UF)": "F073.UFF.PRE.Z.D",
    "Dólar observado": "F073.TCO.PRE.Z.D",
    "Indice de valor promedio (IVP)": "F073.IVP.PRE.Z.D",
    "Tasa de política monetaria (TPM)": "F022.TPM.TIN.D001.NO.Z.D",
    "Tipo de cambio nominal euro": "F072.CLP.EUR.N.O.D",
}

#: Series con publicación mensual/trimestral (contexto económico amplio).
SERIES_BDE_PERIODICAS: dict[str, str] = {
    "IMACEC (índice mensual, base 2018=100)": "F032.IMC.IND.Z.Z.EP18.Z.Z.0.M",
    "PIB (volumen trimestral, millones CLP)": "F032.PIB.FLU.R.CLP.EP18.Z.Z.0.T",
    "IPC (índice mensual, empalme base 2023=100)": "G073.IPC.IND.2023.M",
}


def _token_bde() -> str:
    return os.getenv("BCENTRAL_TOKEN", "").strip()


def _parsear_obs_bde(obs: list) -> list[tuple[datetime, str]]:
    """Observaciones BDE → [(fecha, valor), ...] válidas.

    Formato real: [{'indexDateString': '30-07-2026', 'value': '935.57',
                     'statusCode': 'OK'}, ...]. Fines de semana vienen como
    'NaN' con statusCode 'ND' y se omiten. Se acepta también el formato
    [fecha, valor] por compatibilidad.
    """
    puntos: list[tuple[datetime, str]] = []
    for o in obs:
        try:
            if isinstance(o, dict):
                fecha_str = str(o.get("indexDateString", ""))
                valor = str(o.get("value", ""))
                status = str(o.get("statusCode", ""))
            else:
                fecha_str, valor, status = str(o[0]), str(o[1]), "OK"
            if status != "OK" or not valor or valor.upper() in {"NAN", "ND", "N/A"}:
                continue
            fecha_str = fecha_str.strip()
            for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
                try:
                    fecha = datetime.strptime(fecha_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                continue
            puntos.append((fecha, valor))
        except (ValueError, IndexError, TypeError):
            continue
    return puntos


def _consultar_serie_bde(codigo: str) -> list[tuple[datetime, str]] | None:
    """Últimas observaciones válidas de una serie BDE: [(fecha, valor), ...]."""
    try:
        resp = requests.get(
            URL_API,
            params={
                "token": _token_bde(),
                "function": "GetSeries",
                "timeseries": codigo,
            },
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        raw = resp.content.decode("latin-1")
        data = json.loads(raw)
    except (requests.RequestException, ValueError, UnicodeDecodeError) as e:
        logger.warning(f"BCentral API error ({codigo}): {e}")
        return None
    if data.get("Codigo") != 0 or not data.get("Series"):
        logger.warning(f"BCentral API rechazó serie {codigo}: {data.get('Descripcion')}")
        return None
    obs = data["Series"].get("Obs")
    if not isinstance(obs, list) or not obs:
        return None
    return _parsear_obs_bde(obs)[-7:]


def _redondear(valor: str) -> str:
    """Redondea un valor numérico a 2 decimales sin romper formatos especiales."""
    try:
        return f"{float(valor):.2f}"
    except ValueError:
        return valor


def _items_para_series(
    series: dict[str, str],
    fuente: str,
    tags: list[str],
    contexto: str,
    limite: int,
) -> list[ItemInformativo]:
    """Convierte una o más series BDE en items informativos (último valor)."""
    if not _token_bde():
        logger.info("BCentral: sin BCENTRAL_TOKEN, se omite la API BDE")
        return []

    items: list[ItemInformativo] = []
    for nombre, codigo in series.items():
        puntos = _consultar_serie_bde(codigo)
        if not puntos:
            continue
        fecha, valor = puntos[-1]
        valor = _redondear(valor)
        items.append(ItemInformativo(
            id=f"bde-{fuente}-{len(items)}",
            titulo=f"{nombre}: {valor}",
            fuente=fuente,
            contenido=(
                f"Indicador oficial del Banco Central de Chile (API BDE) al "
                f"{fecha.strftime('%d/%m/%Y')}: {nombre} = {valor}. {contexto}".rstrip()
            ),
            url=URL_API,
            fecha=fecha,
            tags=tags,
            nodo_sugerido="ECONOMIA",
        ))
        logger.info(
            f"BCentral API: {nombre} ({codigo}) → {valor} al {fecha.strftime('%d/%m/%Y')}"
        )

    if not items:
        logger.warning("BCentral API: no se obtuvo ninguna serie válida")
    return items[:limite]


def obtener_items_bde(limite: int = 20) -> list[ItemInformativo]:
    """Indicadores económicos diarios vía API BDE oficial."""
    return _items_para_series(
        SERIES_BDE,
        fuente="bcentral-bde",
        tags=["bcentral", "bde", "economia"],
        contexto="",
        limite=limite,
    )


def obtener_items_bde_periodicos(limite: int = 10) -> list[ItemInformativo]:
    """Contexto económico mensual/trimestral (IMACEC, PIB, IPC) vía API BDE."""
    return _items_para_series(
        SERIES_BDE_PERIODICAS,
        fuente="bcentral-bde-periodica",
        tags=["bcentral", "bde", "economia", "contexto"],
        contexto="Publicación mensual/trimestral del Banco Central de Chile.",
        limite=limite,
    )
