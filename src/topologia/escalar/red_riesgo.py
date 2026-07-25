from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from topologia.escalar.compuesto import RiesgoCultural
from topologia.escalar.indices import NODOS_ACTIVOS
from topologia.paths import get_reportes_dir

if TYPE_CHECKING:
    from topologia.models.schemas import EstadoCultural

_REDES_DIR = None


def _get_redes_dir() -> Path:
    global _REDES_DIR
    if _REDES_DIR is None:
        _REDES_DIR = get_reportes_dir() / "redes_riesgo"
        _REDES_DIR.mkdir(parents=True, exist_ok=True)
    return _REDES_DIR


def exportar_red(
    riesgo: RiesgoCultural,
    actual: EstadoCultural,
    historial: list[EstadoCultural] | None = None,
) -> Path:
    fecha_str = riesgo.fecha.strftime("%Y-%m-%d")
    salida = _get_redes_dir() / f"red_riesgo_{fecha_str}.json"

    nodes = []
    nodes.append({
        "id": "R_compuesto",
        "label": "Riesgo Compuesto",
        "tipo": "escalar",
        "valor": riesgo.R_compuesto,
        "alerta": riesgo.alerta,
    })
    for comp_id, comp_label in [
        ("delta_proximidad", "Proximidad a hitos"),
        ("m_contraccion", "Contraccion M"),
        ("theta_desviacion", "Desviacion de theta"),
        ("v_trabajo_norm", "Velocidad TRABAJO"),
        ("s_activacion", "Activacion SEXUALIDAD"),
        ("co_sincronia", "Co-sincronia"),
    ]:
        nodes.append({
            "id": comp_id,
            "label": comp_label,
            "tipo": "componente",
            "valor": getattr(riesgo, comp_id, 0.0),
        })

    for n in actual.nodos:
        if n.nodo_id in NODOS_ACTIVOS:
            nodes.append({
                "id": n.nodo_id,
                "label": n.nodo_id.capitalize(),
                "tipo": "nodo_cultural",
                "delta": round(n.delta, 2),
                "M_m": round(n.dimension_m, 2),
                "M_l": round(n.dimension_l, 2),
                "M_s": round(n.dimension_s, 2),
                "fragil": n.fragil,
            })

    edges = []

    for comp_id in ["delta_proximidad", "m_contraccion", "theta_desviacion", "co_sincronia"]:
        edges.append({
            "source": "R_compuesto",
            "target": comp_id,
            "weight": round(riesgo.pesos_usados.get(comp_id, 0), 4),
            "tipo": "peso_componente",
        })

    edges.append({
        "source": "v_trabajo_norm",
        "target": "TRABAJO",
        "weight": 1.0,
        "tipo": "dependencia_nodal",
    })
    edges.append({
        "source": "s_activacion",
        "target": "SEXUALIDAD",
        "weight": 1.0,
        "tipo": "dependencia_nodal",
    })
    sync_nodes = ["ECONOMIA", "TRABAJO", "SEXUALIDAD"]
    for i in range(len(sync_nodes)):
        for j in range(i + 1, len(sync_nodes)):
            edges.append({
                "source": f"co_sincronia",
                "target": sync_nodes[j],
                "weight": 0.5,
                "tipo": "sincronia_parcial",
            })

    for n in actual.nodos:
        if n.nodo_id in NODOS_ACTIVOS and n.delta > 5:
            edges.append({
                "source": n.nodo_id,
                "target": "R_compuesto",
                "weight": round(min(n.delta / 25.0, 1.0), 4),
                "tipo": "contribucion_delta",
            })

    historial_vals = []
    fechas = []
    if historial and len(historial) > 0:
        for est in historial:
            fechas.append(est.fecha.isoformat())
            m = {n.nodo_id: n.delta for n in est.nodos}
            historial_vals.append({nid: m.get(nid, 0) for nid in NODOS_ACTIVOS})

    graph = {
        "metadatos": {
            "fecha": fecha_str,
            "version": 1,
            "nodos_activos": NODOS_ACTIVOS,
            "alerta": riesgo.alerta,
            "R_compuesto": riesgo.R_compuesto,
        },
        "nodes": nodes,
        "edges": edges,
        "time_series": {
            "fechas": fechas,
            "valores": historial_vals,
        },
    }

    with open(salida, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    return salida


def listar_redes() -> list[Path]:
    directorio = _get_redes_dir()
    return sorted(directorio.glob("red_riesgo_*.json"))


def cargar_red(fecha: str) -> dict | None:
    ruta = _get_redes_dir() / f"red_riesgo_{fecha}.json"
    if not ruta.exists():
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)
