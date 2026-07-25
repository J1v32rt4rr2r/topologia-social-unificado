from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from topologia.models.schemas import EstadoCultural

NODOS_ACTIVOS = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION",
]

_CONFIG = None


def _cargar_config() -> dict:
    global _CONFIG
    if _CONFIG is None:
        ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "escalar_riesgo.json"
        with open(ruta, encoding="utf-8") as f:
            _CONFIG = json.load(f)
    return _CONFIG


def _vector_delta(estado: EstadoCultural) -> list[float]:
    m = {n.nodo_id: n.delta for n in estado.nodos}
    return [m.get(n, 0.0) for n in NODOS_ACTIVOS]


def _cargar_hitos() -> list[dict]:
    import yaml
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "hitos.yaml"
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _dist_euclidiana(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def delta_proximidad(actual: EstadoCultural) -> float:
    cfg = _cargar_config()
    max_dist = cfg["componentes"][0]["parametros"]["max_distancia_historica"]
    vec_actual = _vector_delta(actual)
    hitos = _cargar_hitos()
    if not hitos:
        return 0.0
    dist_min = min(
        _dist_euclidiana(vec_actual, [h["nodos"][n]["delta"] for n in NODOS_ACTIVOS])
        for h in hitos
    )
    return max(0.0, min(1.0, 1.0 - dist_min / max_dist))


def m_contraccion(actual: EstadoCultural) -> float:
    cfg = _cargar_config()
    p = cfg["componentes"][1]["parametros"]
    baseline = p["baseline_M"]
    minimo = p["min_M"]
    suma = actual.M_m + actual.M_l + actual.M_s
    raw = 1.0 - (suma - minimo) / (baseline - minimo)
    return max(0.0, min(1.0, raw))


def theta_desviacion(actual: EstadoCultural) -> float:
    cfg = _cargar_config()
    p = cfg["componentes"][2]["parametros"]
    base = p["theta_base"]
    rango = p["rango_theta"]
    raw = abs(actual.theta_cultura - base) / rango
    return max(0.0, min(1.0, raw))


def _velocidad_nodo(historial: list[EstadoCultural], nodo_id: str) -> float:
    if len(historial) < 2:
        return 0.0
    a = historial[-2]
    b = historial[-1]
    days = max((b.fecha - a.fecha).total_seconds() / 86400, 1.0)
    delta_a = next((n.delta for n in a.nodos if n.nodo_id == nodo_id), 0.0)
    delta_b = next((n.delta for n in b.nodos if n.nodo_id == nodo_id), 0.0)
    return (delta_b - delta_a) / days


def v_trabajo_norm(historial: list[EstadoCultural]) -> float:
    cfg = _cargar_config()
    max_v = cfg["componentes"][3]["parametros"]["max_v_historica"]
    v = _velocidad_nodo(historial, "TRABAJO")
    return max(0.0, min(1.0, abs(v) / max_v))


def s_activacion(actual: EstadoCultural) -> float:
    cfg = _cargar_config()
    max_delta = cfg["componentes"][4]["parametros"]["max_delta_historica"]
    for n in actual.nodos:
        if n.nodo_id == "SEXUALIDAD":
            return max(0.0, min(1.0, n.delta / max_delta))
    return 0.0


def co_sincronia(historial: list[EstadoCultural]) -> float:
    cfg = _cargar_config()
    ventana = cfg["componentes"][5]["parametros"]["ventana_minima"]
    nodos_sync = cfg["componentes"][5]["parametros"]["nodos"]
    if len(historial) < ventana:
        return 0.0
    series = {nid: [] for nid in nodos_sync}
    for est in historial:
        for n in est.nodos:
            if n.nodo_id in series:
                series[n.nodo_id].append(n.delta)
    corrs = []
    for i in range(len(nodos_sync)):
        for j in range(i + 1, len(nodos_sync)):
            a = series[nodos_sync[i]]
            b = series[nodos_sync[j]]
            n = len(a)
            ma, mb = sum(a) / n, sum(b) / n
            num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
            den = math.sqrt(sum((x - ma) ** 2 for x in a)) * math.sqrt(sum((y - mb) ** 2 for y in b))
            if den:
                corrs.append(abs(num / den))
    return sum(corrs) / len(corrs) if corrs else 0.0
