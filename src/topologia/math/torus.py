from __future__ import annotations

import math
from typing import Sequence


def calcular_angulos(valor_m: float, valor_l: float, valor_s: float) -> tuple[float, float, float]:
    theta_m = 360.0 / max(valor_m, 0.1)
    theta_l = 360.0 / max(valor_l, 0.1)
    theta_s = 360.0 / max(valor_s, 0.1)
    return (theta_m, theta_l, theta_s)


def calcular_delta(angulos: Sequence[float]) -> float:
    media = sum(angulos) / len(angulos)
    varianza = sum((a - media) ** 2 for a in angulos) / len(angulos)
    return math.sqrt(varianza)


def mapear_a_toro_3d(
    valor_m: float,
    valor_l: float,
    valor_s: float,
    R: float = 2.0,
    r: float = 1.0,
) -> tuple[float, float, float, float, float]:
    u = (valor_m / 9.9) * 2 * math.pi
    v = (valor_l / 9.9) * 2 * math.pi
    x = (R + r * math.cos(u)) * math.cos(v)
    y = (R + r * math.cos(u)) * math.sin(v)
    z = r * math.sin(u)
    intensidad = valor_s / 9.9
    return (x, y, z, intensidad, u)


def coherencia_global(nodos_valores: list[tuple[float, float, float]]) -> dict:
    if not nodos_valores:
        return {"M_m": 0, "M_l": 0, "M_s": 0, "delta_promedio": 0, "coherente": True}
    M_m = sum(v[0] for v in nodos_valores) / len(nodos_valores)
    M_l = sum(v[1] for v in nodos_valores) / len(nodos_valores)
    M_s = sum(v[2] for v in nodos_valores) / len(nodos_valores)
    deltas = []
    for v in nodos_valores:
        angulos = calcular_angulos(v[0], v[1], v[2])
        deltas.append(calcular_delta(angulos))
    delta_prom = sum(deltas) / len(deltas) if deltas else 0
    return {
        "M_m": M_m,
        "M_l": M_l,
        "M_s": M_s,
        "delta_promedio": delta_prom,
        "coherente": delta_prom < 70.0,
        "nodos_fragiles": sum(1 for d in deltas if d >= 70),
    }
