"""
Módulo de Google Trends para obtener tendencias de búsqueda en Chile
como parte de la Fase 4 (discursiva de masas).

Usa pytrends (librería no oficial pero ampliamente usada).
Mide el interés relativo de búsqueda de términos clave chilenos,
sin identificar usuarios individuales.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo

# Términos de búsqueda representativos para cada nodo cultural
TERMINOS_CLAVE = [
    # Economía
    "inflacion Chile", "sueldo minimo Chile", "IPC Chile",
    "cotizacion dolar Chile", "afp Chile",
    # Trabajo
    "cesantia Chile", "empleo Chile", "trabajo Chile",
    "sueldo Chile", "jornada laboral Chile",
    # Política
    "gobierno Chile", "kast", "boric",
    "congreso Chile", "elecciones Chile",
    # Continuidad / Identidad
    "crisis Chile", "inmigracion Chile",
    "Chile pais", "mapuche",
    # Lenguaje / Educación
    "PACE Chile", "educacion Chile", "universidad Chile",
    # Salud / Bienestar
    "isapres Chile", "salud Chile", "fono Chile",
    # Tecnología
    "internet Chile", "celular Chile",
    # Clima / Emergencia
    "temporal Chile", "sistema frontal Chile",
]

_ultima_llamada: float = 0.0
_DELAY = 5.0  # pytrends es sensible a rate limiting


def _esperar() -> None:
    global _ultima_llamada
    ahora = time.time()
    diff = ahora - _ultima_llamada
    if diff < _DELAY:
        time.sleep(_DELAY - diff)
    _ultima_llamada = time.time()


def obtener_tendencias(
    terminos: list[str] | None = None,
    timeframe: str = "now 7-d",
    max_items: int = 20,
) -> list[ItemInformativo]:
    """
    Obtiene tendencias de búsqueda de Google Trends para Chile.

    Args:
        terminos: Lista de términos a consultar. Si es None usa TERMINOS_CLAVE.
        timeframe: Ventana de tiempo (formato pytrends: "now 7-d", "today 1-m", etc.).
        max_items: Máximo de items a retornar.

    Returns:
        Lista de ItemInformativo con los términos de mayor interés relativo.
    """
    if terminos is None:
        terminos = TERMINOS_CLAVE

    try:
        from pytrends.request import TrendReq
    except ImportError:
        logger.error("pytrends no instalado: pip install pytrends")
        return []

    try:
        _esperar()
        # Configurar conexión con User-Agent del proyecto
        from requests import Session
        session = Session()
        session.headers.update({
            "User-Agent": (
                "TopologiaSocial/2.0 "
                "(Proyecto de investigacion sociologica; "
                "monitoreo de clima cultural chileno)"
            )
        })
        pytrends = TrendReq(
            hl="es-CL",
            tz=180,  # UTC-3 (Chile)
            requests_args={"headers": session.headers},
        )

        resultados: list[ItemInformativo] = []
        items_count = 0

        # Consultar en lotes de 5 términos (límite de pytrends)
        for i in range(0, len(terminos), 5):
            if items_count >= max_items:
                break
            lote = terminos[i:i + 5]
            _esperar()
            try:
                pytrends.build_payload(
                    kw_list=lote,
                    cat=0,
                    timeframe=timeframe,
                    geo="CL",
                    gprop="",
                )
                data = pytrends.interest_over_time()
                if data.empty:
                    continue
                # La última fila tiene los valores más recientes
                ultima_fila = data.iloc[-1]
                fecha = datetime.now(timezone.utc)
                if hasattr(data.index[-1], "to_pydatetime"):
                    fecha = data.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)

                for kw in lote:
                    if kw in data.columns:
                        valor = int(ultima_fila[kw])
                        if valor > 0:
                            resultados.append(ItemInformativo(
                                id=f"trends-{len(resultados)}",
                                titulo=f"Tendencia: {kw}",
                                fuente="google_trends",
                                contenido=f"Interés relativo: {valor}/100 en Chile ({timeframe})",
                                url=f"https://trends.google.com/trends/explore?geo=CL&q={kw}",
                                fecha=fecha,
                                tags=["google_trends", kw],
                            ))
                            items_count += 1
            except Exception as e:
                logger.debug(f"Google Trends lote {lote}: {e}")
                continue

        logger.info(f"Google Trends: {len(resultados)} términos con interés > 0")
        return resultados[:max_items]

    except Exception as e:
        logger.error(f"Google Trends error general: {e}")
        return []
