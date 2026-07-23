from __future__ import annotations

import json
from pathlib import Path

from topologia.logger import logger
from topologia.models.schemas import EstrategiaRecoleccion
from topologia.paths import get_data_dir
from topologia.web.brechas import NODOS_CULTURALES


def _cargar_timeline() -> list[dict]:
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "data" / "barrido" / "timeline.json"
    if not ruta.exists():
        logger.warning("No hay timeline.json para análisis histórico")
        return []
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _tendencia_delta(valores: list[float]) -> str:
    if len(valores) < 3:
        return "estable"
    pendiente = (valores[-1] - valores[0]) / max(len(valores) - 1, 1)
    if pendiente > 3:
        return "subiendo"
    if pendiente < -3:
        return "bajando"
    return "estable"


def _dimensional_drift(nodo_data: list[dict]) -> str | None:
    if len(nodo_data) < 2:
        return None
    vars = {"m": 0.0, "l": 0.0, "s": 0.0}
    first = nodo_data[0]
    last = nodo_data[-1]
    for dim in vars:
        vars[dim] = abs(last.get(dim, 5.0) - first.get(dim, 5.0))
    max_dim = max(vars, key=vars.get)
    if vars[max_dim] > 2.0:
        return {"m": "M_m", "l": "M_l", "s": "M_s"}[max_dim]
    return None


def diagnosticar(sociedad: str = "Chile") -> EstrategiaRecoleccion:
    timeline = _cargar_timeline()
    if not timeline:
        logger.info("Sin historial, usando estrategia por defecto")
        return EstrategiaRecoleccion(sociedad=sociedad)

    solo_chile = [r for r in timeline if r.get("fecha", "").startswith("2026")]
    if not solo_chile:
        return EstrategiaRecoleccion(sociedad=sociedad)

    data = solo_chile
    n = len(data)

    nodos_prioritarios: list[str] = []
    nodos_con_brecha: list[str] = []
    dimensiones_inestables: dict[str, str] = {}

    for nodo_id in NODOS_CULTURALES:
        nodo_vals: list[float] = []
        nodo_data: list[dict] = []
        fragil_count = 0

        for r in data:
            nd = r.get(nodo_id)
            if nd is None:
                continue
            d = nd.get("delta", 0)
            nodo_vals.append(d)
            nodo_data.append(nd)
            if nd.get("fragil") == "SI":
                fragil_count += 1

        if not nodo_vals:
            nodos_con_brecha.append(nodo_id)
            nodos_prioritarios.append(nodo_id)
            continue

        # Fragilidad histórica
        freq_fragil = fragil_count / max(n, 1)
        if freq_fragil > 0.2:
            nodos_prioritarios.append(nodo_id)

        # Tendencia de delta
        tend = _tendencia_delta(nodo_vals)
        if tend == "subiendo":
            nodos_prioritarios.append(nodo_id)

        # Dimensional drift
        dim = _dimensional_drift(nodo_data)
        if dim:
            dimensiones_inestables[nodo_id] = dim
            if nodo_id not in nodos_prioritarios:
                nodos_prioritarios.append(nodo_id)

        # Brecha: si el delta es 0 en múltiples registros (score plano)
        planos = sum(1 for v in nodo_vals if v < 5.0)
        if planos > n * 0.4:
            nodos_con_brecha.append(nodo_id)

    # Último estado para métricas actuales
    ultimo = data[-1]
    umbral = 0.5
    if ultimo.get("delta", 30) > 30:
        umbral = 0.4
    if not nodos_prioritarios:
        umbral = 0.3

    estrategia = EstrategiaRecoleccion(
        sociedad=sociedad,
        nodos_prioritarios=list(set(nodos_prioritarios)),
        nodos_con_brecha=list(set(nodos_con_brecha)),
        dimensiones_inestables=dimensiones_inestables,
        umbral_relevancia=umbral,
        max_items_por_nodo=15 if nodos_prioritarios else 10,
    )

    logger.info(
        f"Diagnóstico: {len(estrategia.nodos_prioritarios)} prioritarios, "
        f"{len(estrategia.nodos_con_brecha)} con brecha, "
        f"{len(estrategia.dimensiones_inestables)} con drift dimensional, "
        f"umbral={umbral}"
    )
    return estrategia
