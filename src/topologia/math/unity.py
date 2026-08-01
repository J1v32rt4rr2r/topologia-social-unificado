"""Núcleo matemático del ente fractal: el UNO y el tecelado social.

Axiomas implementados:
    U — Unidad:      I(u) = e^{2πi} = 1 (identidad invariante).
    F — Falsabilidad: el contenido M es no-real → se codifica como e^{-2πiM}.
    O — Operatividad: x ↦ -1/x (involución); u_op = e^{2πi/M}.
    D — Densidad:    concentración del tecelado alrededor de la fase dominante θ*.
"""

from __future__ import annotations

import cmath
import math
from typing import Sequence

from topologia.models.schemas import EvaluacionNodo

CANALES = ("M", "L", "S")
EPS_DEFAULT = 30.0


def identidad() -> complex:
    """Axioma U: la identidad del ente es e^{2πi} = 1 (invariante)."""
    return 1.0 + 0j


def estado_falsificable(M: float) -> complex:
    """Axioma F: e^{-2πiM} — el contenido falsificable (no-real).

    Para M entero colapsa a la identidad: lo no-real no distingue.
    """
    return cmath.exp(-2j * math.pi * max(M, 0.001))


def inversa_negativa(x: float) -> float:
    """Axioma O: x ↦ -1/x. Involución: aplicarla dos veces devuelve x."""
    if x == 0.0:
        raise ValueError("inversa_negativa no está definida para x = 0")
    return -1.0 / x


def estado_operativo(M: float) -> complex:
    """Axioma O: e^{2πi/M} — el estado computable (positivación del contenido)."""
    return cmath.exp(2j * math.pi / max(M, 0.001))


def mapeo_valoracion(v: float) -> tuple[float, complex]:
    """v ∈ [0,10] → (θ grados, p = e^{iθ}) — rayo de la lógica y vértice de contacto."""
    theta = 360.0 / max(v, 0.1)
    p = cmath.exp(1j * math.radians(theta))
    return theta, p


def tecelado(nodos: Sequence[EvaluacionNodo]) -> dict[str, complex]:
    """Los 27 vértices p_{kj} = e^{iθ_{kj}} (lógica k × nodo j) sobre el cuerpo unitario."""
    t: dict[str, complex] = {}
    for nodo in nodos:
        for canal in CANALES:
            v = getattr(nodo, f"dimension_{canal.lower()}")
            _, p = mapeo_valoracion(v)
            t[f"{nodo.nodo_id}:{canal}"] = p
    return t


def fase_dominante(m_m: float, m_l: float, m_s: float) -> tuple[str, float]:
    """El núcleo del ente: canal de mayor masa k* y su fase θ* = 360°/M_{k*}."""
    canales = {"M": m_m, "L": m_l, "S": m_s}
    k_star = max(canales, key=canales.get)
    return k_star, 360.0 / max(canales[k_star], 0.1)


def diferencia_angular(p1: complex, p2: complex) -> float:
    """Distancia angular mínima entre dos puntos del círculo (radianes)."""
    d = abs(cmath.phase(p1) - cmath.phase(p2))
    return min(d, 2 * math.pi - d)


def densidad(puntos: Sequence[complex], nucleo: complex, eps: float = EPS_DEFAULT) -> dict:
    """Concentración del tecelado alrededor del núcleo (Axioma D).

    R: resultant length (R → 1 = dominancia máxima, R → 0 = uniforme).
    D: fracción de vértices dentro de la ventana ε (el "corte" del hiperplano).
    """
    if not puntos:
        return {"R": 0.0, "D": 0.0, "n": 0}
    fase_nucleo = cmath.phase(nucleo)
    fases = [cmath.phase(p) for p in puntos]
    R = abs(sum(cmath.exp(1j * (f - fase_nucleo)) for f in fases) / len(puntos))
    eps_rad = math.radians(eps)
    D = sum(1 for p in puntos if diferencia_angular(p, nucleo) <= eps_rad) / len(puntos)
    return {"R": R, "D": D, "n": len(puntos)}


def arrastre(p: complex, nucleo: complex, R: float, delta_theta: float, lam: float = 0.5) -> complex:
    """Posición efectiva bajo arrastre: p* = p + λ·R·f(Δθ)·(núcleo − p).

    Δθ en radianes; f(Δθ) = min(Δθ/π, 1) acotada en [0, 1].
    """
    f = min(delta_theta / math.pi, 1.0)
    return p + lam * R * f * (nucleo - p)
