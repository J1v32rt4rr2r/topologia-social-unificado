from __future__ import annotations

import cmath
import math
from typing import Sequence


# ─── Funciones orbitales (nuevo modelo) ─────────────────────


def angulo_desde_valor(valor: float) -> float:
    """θ = 360° / v   (equivalente a e^(2πi/v) en el plano complejo)"""
    return 360.0 / max(valor, 0.1)


def theta_nodo(M_l: float) -> float:
    """Dirección orbital del nodo en el plano cultural."""
    return angulo_desde_valor(M_l)


def theta_cultura(nodos_ml: Sequence[float]) -> float:
    """Centro cultural = 360° / promedio(M_l de todos los nodos)."""
    if not nodos_ml:
        return 0.0
    return angulo_desde_valor(sum(nodos_ml) / len(nodos_ml))


def arrastre_gravimetrico(M_m: float, M_s: float, delta_theta: float) -> float:
    """Fuerza con que un nodo arrastra al sistema: peso × volumen × desalineación."""
    return M_m * M_s * abs(delta_theta)


def tension_sistema(nodos: list[dict]) -> float:
    """Tensión total del sistema = Σ(M_m × |θ_cultura - θ_nodo|)."""
    if not nodos:
        return 0.0
    nodos_ml = [n.get("dimension_l", n.get("l", 5.0)) for n in nodos]
    t_cultura = theta_cultura(nodos_ml)
    total = 0.0
    for n in nodos:
        ml = n.get("dimension_l", n.get("l", 5.0))
        mm = n.get("dimension_m", n.get("m", 5.0))
        tn = theta_nodo(ml)
        total += mm * abs(t_cultura - tn)
    return total


def detectar_vuelco(tension: float, umbral: float = 500.0) -> bool:
    """True si la tensión acumulada supera el umbral — se dispara vuelco de fase."""
    return tension >= umbral


# ─── Formas culturales complejas (e^(2πi / t), t = M) ───────


def forma_cultural_compleja(M: float) -> complex:
    """F = e^(2πi / M) — forma cultural como número complejo en el plano.

    t = M es la magnitud cultural; el número complejo unitario
    codifica coherencia (parte real) y tensión transformadora (parte imaginaria).
    """
    return cmath.exp(2j * math.pi / max(M, 0.001))


def forma_transversal(valores: list[float]) -> dict:
    """Calcula M = Σ(v) y F = e^(2πi / M) para un conjunto de valores nodales.

    Returns
    -------
    dict con keys: 'M' (suma), 'F' (complex), 'angulo' (radianes).
    """
    M = sum(valores)
    F = forma_cultural_compleja(M)
    return {"M": M, "F": F, "angulo": cmath.phase(F)}


def diferencia_angular(F1: complex, F2: complex) -> float:
    """Diferencia angular absoluta entre dos formas culturales (radianes)."""
    d = abs(cmath.phase(F1) - cmath.phase(F2))
    return min(d, 2 * math.pi - d)


def coherencia_formas(formas: list[complex]) -> float:
    """Coherencia promedio entre N formas culturales (radianes)."""
    if len(formas) < 2:
        return 0.0
    diffs = []
    for i in range(len(formas)):
        for j in range(i + 1, len(formas)):
            diffs.append(diferencia_angular(formas[i], formas[j]))
    return sum(diffs) / len(diffs)


# ─── Funciones originales (compatibilidad con agentes) ───────


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
