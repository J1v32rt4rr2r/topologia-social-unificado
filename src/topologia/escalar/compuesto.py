from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from topologia.escalar.indices import (
    NODOS_ACTIVOS,
    co_sincronia,
    delta_proximidad,
    m_contraccion,
    s_activacion,
    theta_desviacion,
    v_trabajo_norm,
)

if TYPE_CHECKING:
    from topologia.models.schemas import EstadoCultural


@dataclass
class RiesgoCultural:
    fecha: datetime
    R_compuesto: float
    delta_proximidad: float
    m_contraccion: float
    theta_desviacion: float
    v_trabajo_norm: float
    s_activacion: float
    co_sincronia: float
    pesos_usados: dict[str, float]
    alerta: str
    desglose: dict[str, float] = field(default_factory=dict)
    nodos_destacados: list[dict] = field(default_factory=list)

    def a_dict(self) -> dict:
        return {
            "fecha": self.fecha.isoformat(),
            "R_compuesto": round(self.R_compuesto, 4),
            "delta_proximidad": round(self.delta_proximidad, 4),
            "m_contraccion": round(self.m_contraccion, 4),
            "theta_desviacion": round(self.theta_desviacion, 4),
            "v_trabajo_norm": round(self.v_trabajo_norm, 4),
            "s_activacion": round(self.s_activacion, 4),
            "co_sincronia": round(self.co_sincronia, 4),
            "pesos_usados": self.pesos_usados,
            "alerta": self.alerta,
            "nodos_destacados": self.nodos_destacados,
        }


def _cargar_pesos() -> dict[str, float]:
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "escalar_riesgo.json"
    with open(ruta, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["pesos_iniciales"]


def _evaluar_alerta(R: float) -> str:
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "escalar_riesgo.json"
    with open(ruta, encoding="utf-8") as f:
        cfg = json.load(f)
    umbrales = cfg["umbrales"]
    if R >= umbrales["alerta_roja"]:
        return "ROJA"
    if R >= umbrales["alerta_amarilla"]:
        return "AMARILLA"
    return "VERDE"


def calcular_riesgo(
    actual: EstadoCultural,
    historial: list[EstadoCultural] | None = None,
    pesos: dict[str, float] | None = None,
) -> RiesgoCultural:
    if historial is None:
        historial = [actual]
    if pesos is None:
        pesos = _cargar_pesos()

    d_prox = delta_proximidad(actual)
    m_cont = m_contraccion(actual)
    t_dev = theta_desviacion(actual)
    v_trab = v_trabajo_norm(historial)
    s_act = s_activacion(actual)
    co_sync = co_sincronia(historial)

    componentes = {
        "delta_proximidad": d_prox,
        "m_contraccion": m_cont,
        "theta_desviacion": t_dev,
        "v_trabajo_norm": v_trab,
        "s_activacion": s_act,
        "co_sincronia": co_sync,
    }

    R = sum(pesos[k] * componentes[k] for k in pesos)
    R = max(0.0, min(1.0, R))

    alerta = _evaluar_alerta(R)

    desglose = {k: round(v, 4) for k, v in sorted(componentes.items(), key=lambda x: x[1], reverse=True)}

    nodos_destacados = []
    for n in actual.nodos:
        if n.nodo_id in NODOS_ACTIVOS and n.delta > 10:
            nodos_destacados.append({
                "nodo": n.nodo_id,
                "delta": round(n.delta, 1),
                "etiqueta": "CRITICO" if n.delta > 20 else "ALTO",
            })

    return RiesgoCultural(
        fecha=actual.fecha,
        R_compuesto=round(R, 4),
        delta_proximidad=round(d_prox, 4),
        m_contraccion=round(m_cont, 4),
        theta_desviacion=round(t_dev, 4),
        v_trabajo_norm=round(v_trab, 4),
        s_activacion=round(s_act, 4),
        co_sincronia=round(co_sync, 4),
        pesos_usados=pesos,
        alerta=alerta,
        desglose=desglose,
        nodos_destacados=nodos_destacados,
    )
