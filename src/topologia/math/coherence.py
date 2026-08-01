"""Evaluación de entes fractales: la misma lógica en toda escala (Axioma S).

Un ente (persona, grupo, clase o sociedad) se evalúa con la misma operación:
tecelado de 27 vértices, fase dominante θ*, densidad alrededor del núcleo
y vértices efectivos bajo arrastre.
"""

from __future__ import annotations

import cmath
import math

from topologia.math.unity import arrastre, densidad, diferencia_angular, fase_dominante, tecelado
from topologia.models.schemas import EnteFractal, EstadoCultural, TipoEnte


def evaluar_ente_fractal(
    estado: EstadoCultural,
    nombre: str = "",
    tipo: TipoEnte = TipoEnte.grupo,
    lam: float = 0.5,
) -> EnteFractal:
    """Aplica el núcleo del UNO a un estado cultural en cualquier nivel fractal."""
    t = tecelado(estado.nodos)
    k_star, theta_star = fase_dominante(estado.m_m, estado.m_l, estado.m_s)
    nucleo = cmath.exp(1j * math.radians(theta_star))
    puntos = list(t.values())
    dens = densidad(puntos, nucleo)
    efectivos = {
        clave: arrastre(p, nucleo, dens["R"], diferencia_angular(p, nucleo), lam=lam)
        for clave, p in t.items()
    }
    return EnteFractal(
        nombre=nombre or estado.sociedad,
        tipo=tipo,
        nivel_fractal=estado.nivel_fractal,
        estado=estado,
        nucleo=k_star,
        theta_nucleo=theta_star,
        densidad_R=dens["R"],
        densidad_D=dens["D"],
        tecelado=t,
        tecelado_efectivo=efectivos,
    )
