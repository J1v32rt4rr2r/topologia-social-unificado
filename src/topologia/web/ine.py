"""INE — Instituto Nacional de Estadísticas de Chile (fuente oficial).

Tres bloques parseados del sitio oficial (renderizado en servidor):

1. Indicadores destacados del home: IPC, Índice Nominal de Remuneraciones,
   Tasa de desocupación, Población total y Esperanza de vida, cada uno con
   valor y período de referencia.
2. Publicaciones recientes de sala de prensa (título + fecha + URL).
3. Agenda estadística: próximas publicaciones oficiales programadas.

El sitio no expone RSS ni una API pública resoluble desde esta red, por lo
que se usa scraping (mismo patrón que bcentral.py).
"""

from __future__ import annotations

import calendar
import html as _html
import re
import time
from datetime import datetime, timezone
from typing import Any

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
TIMEOUT = 20

URL_HOME = "https://www.ine.gob.cl/"
URL_AGENDA = "https://www.ine.gob.cl/inicio/agendaestadistica/"

_TTL_CACHE = 12 * 3600
_CACHE: dict[str, tuple[float, list[ItemInformativo]]] = {}

_MESES: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

#: Widgets de indicadores del home: <h1>título</h1>, <p class="cifraV3">valor,
#: <p class="periodoCifraV3">período.
_RE_INDICADOR = re.compile(
    r'<div class="indicadorPrincipalHomeV3[^"]*">.*?'
    r"<h1>(.*?)</h1>.*?"
    r'<p class="cifraV3">(.*?)</p>.*?'
    r'<p class="periodoCifraV3">(.*?)</p>',
    re.S,
)

#: Noticias de sala de prensa en el home: URL + titular + fecha dd-mm-yyyy.
_RE_NOTICIA = re.compile(
    r'<a href="([^"]+)" class="contLinkNoticiaHome">.*?'
    r'<span class="noticiaHomeTitular">(.*?)</span>.*?'
    r'<span class="fechaNoticia">\s*(\d{2})-(\d{2})-(\d{4})\s*</span>',
    re.S,
)

_RE_MES_AGENDA = re.compile(r'<h1 class="tituloMesEaV2">\s*(\w+)\s*</h1>')
_RE_EVENTO_AGENDA = re.compile(
    r'<span class="diaea2"><i class="fas fa-calendar-day"></i>\s*(\d{1,2})\s*</span>\s*'
    r'<span class="horaea2">.*?</span>\s*'
    r'<span class="tituloea2">(.*?)</span>',
    re.S,
)


def _obtener_pagina(url: str) -> str | None:
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.RequestException as e:
        logger.warning(f"INE error fetching {url}: {e}")
        return None


def _limpiar(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", texto)
    return _html.unescape(re.sub(r"\s+", " ", texto)).strip()


def _ultimo_dia(mes: int, anio: int) -> datetime:
    return datetime(anio, mes, calendar.monthrange(anio, mes)[1])


def _parsear_periodo(texto: str) -> datetime | None:
    """'mayo 2026' → 31/05/2026; 'abril - junio 2026' → 30/06/2026;
    '30 de junio de 2026' → fecha exacta. None si no se reconoce."""
    limpio = _limpiar(texto).lower()

    m = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", limpio)
    if m and m.group(2) in _MESES:
        return datetime(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))

    m = re.search(r"(\w+)\s*[-–—]\s*(\w+)\s+(\d{4})", limpio)
    if m and m.group(1) in _MESES and m.group(2) in _MESES:
        return _ultimo_dia(_MESES[m.group(2)], int(m.group(3)))

    m = re.search(r"(\w+)\s+(\d{4})", limpio)
    if m and m.group(1) in _MESES:
        return _ultimo_dia(_MESES[m.group(1)], int(m.group(2)))

    return None


def _nodo_para(titulo: str) -> str:
    t = titulo.lower()
    # Económico/mercado laboral primero (p. ej. "Empleo Población Extranjera")
    if any(k in t for k in (
        "consumidor", "precio", "remuneraci", "desocupaci", "empleo",
        "producci", "ventas", "industrial", "comercio", "inflaci",
        "ferias", "transporte", "tur", "inventarios", "vitales", "matadero",
    )):
        return "ECONOMIA"
    if any(k in t for k in (
        "poblaci", "esperanza", "denuncia", "seguridad", "vivienda",
    )):
        return "SOCIEDAD"
    return "ECONOMIA"


def _parsear_indicadores(pagina: str) -> list[dict[str, Any]]:
    indicadores = []
    for m in _RE_INDICADOR.finditer(pagina):
        titulo = _limpiar(m.group(1))
        valor = _limpiar(m.group(2))
        periodo = _limpiar(m.group(3))
        if not titulo or not valor:
            continue
        indicadores.append({
            "titulo": titulo,
            "valor": valor,
            "periodo": periodo,
            "fecha": _parsear_periodo(periodo),
        })
    return indicadores


def _parsear_noticias(pagina: str) -> list[dict[str, Any]]:
    noticias = []
    for m in _RE_NOTICIA.finditer(pagina):
        url = _html.unescape(m.group(1))
        titulo = _limpiar(m.group(2))
        try:
            fecha = datetime(int(m.group(5)), int(m.group(4)), int(m.group(3)))
        except ValueError:
            continue
        if not titulo:
            continue
        noticias.append({"url": url, "titulo": titulo, "fecha": fecha})
    return noticias


def _parsear_agenda(pagina: str) -> list[dict[str, Any]]:
    """Eventos de la agenda estadística con su mes correspondiente."""
    eventos: list[dict[str, Any]] = []
    anio_actual = datetime.now().year

    posiciones = list(_RE_MES_AGENDA.finditer(pagina))
    for i, m_mes in enumerate(posiciones):
        mes = m_mes.group(1).lower()
        if mes not in _MESES:
            continue
        fin = posiciones[i + 1].start() if i + 1 < len(posiciones) else len(pagina)
        bloque = pagina[m_mes.start():fin]
        anio = anio_actual if _MESES[mes] >= datetime.now().month else anio_actual + 1
        for e in _RE_EVENTO_AGENDA.finditer(bloque):
            dia, titulo = int(e.group(1)), _limpiar(e.group(2))
            try:
                fecha = datetime(anio, _MESES[mes], dia)
            except ValueError:
                continue
            eventos.append({"fecha": fecha, "titulo": titulo})
    return eventos


def _items_indicadores() -> list[ItemInformativo]:
    cache_key = URL_HOME
    if cache_key in _CACHE:
        creado, _ = _CACHE[cache_key]
        if time.time() - creado < _TTL_CACHE:
            return _CACHE[cache_key][1]

    pagina = _obtener_pagina(URL_HOME)
    if not pagina:
        return []

    items: list[ItemInformativo] = []
    for i, ind in enumerate(_parsear_indicadores(pagina)):
        nodo = _nodo_para(ind["titulo"])
        fecha = ind["fecha"] or datetime.now(timezone.utc)
        items.append(ItemInformativo(
            id=f"ine-ind-{i}",
            titulo=f"{ind['titulo']}: {ind['valor']}",
            fuente="ine",
            contenido=(
                f"Indicador oficial del Instituto Nacional de Estadísticas (INE) "
                f"de Chile, período {ind['periodo']}: {ind['titulo']} = {ind['valor']}."
            ),
            url=URL_HOME,
            fecha=fecha,
            tags=["ine", "estadisticas", "indicador", nodo.lower()],
            nodo_sugerido=nodo,
        ))

    _CACHE[cache_key] = (time.time(), items)
    logger.info(f"INE indicadores: {len(items)} al home")
    return items


def _items_noticias() -> list[ItemInformativo]:
    pagina = _obtener_pagina(URL_HOME)
    if not pagina:
        return []

    items: list[ItemInformativo] = []
    for i, n in enumerate(_parsear_noticias(pagina)):
        nodo = _nodo_para(n["titulo"])
        items.append(ItemInformativo(
            id=f"ine-not-{i}",
            titulo=n["titulo"],
            fuente="ine",
            contenido=(
                f"Publicación oficial del INE de Chile del "
                f"{n['fecha'].strftime('%d/%m/%Y')}: {n['titulo']}."
            ),
            url=n["url"],
            fecha=n["fecha"],
            tags=["ine", "noticia", nodo.lower()],
            nodo_sugerido=nodo,
        ))
    return items


def obtener_items(limite: int = 15) -> list[ItemInformativo]:
    """Indicadores destacados + noticias recientes del INE."""
    items = _items_indicadores() + _items_noticias()
    return items[:limite]


def obtener_items_agenda(limite: int = 10) -> list[ItemInformativo]:
    """Próximas publicaciones oficiales de la agenda estadística del INE."""
    cache_key = URL_AGENDA
    if cache_key in _CACHE:
        creado, _ = _CACHE[cache_key]
        if time.time() - creado < _TTL_CACHE:
            return _CACHE[cache_key][1][:limite]

    pagina = _obtener_pagina(URL_AGENDA)
    if not pagina:
        return []

    items: list[ItemInformativo] = []
    for i, ev in enumerate(_parsear_agenda(pagina)):
        nodo = _nodo_para(ev["titulo"])
        items.append(ItemInformativo(
            id=f"ine-agenda-{i}",
            titulo=f"[Programado] {ev['titulo']}",
            fuente="ine-agenda",
            contenido=(
                f"Publicación oficial INE programada para el "
                f"{ev['fecha'].strftime('%d/%m/%Y')}: {ev['titulo']}."
            ),
            url=URL_AGENDA,
            fecha=ev["fecha"],
            tags=["ine", "agenda", "proxima_publicacion", nodo.lower()],
            nodo_sugerido=nodo,
        ))

    _CACHE[cache_key] = (time.time(), items)
    logger.info(f"INE agenda: {len(items)} publicaciones programadas")
    return items[:limite]
