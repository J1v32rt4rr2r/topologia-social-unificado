from __future__ import annotations

from fastapi import APIRouter, Query

from topologia.math.operations import detectar_operaciones
from topologia.orchestrator import Orchestrator
from topologia.storage.store import FileStore

router = APIRouter()
orch = Orchestrator()
store = FileStore()


@router.get("/observe")
async def api_observe(sociedad: str = Query("Chile")):
    estado = orch.observar(sociedad)
    operaciones = detectar_operaciones(estado)
    return {
        "sociedad": estado.sociedad,
        "fecha": estado.fecha.isoformat(),
        "M_m": estado.M_m,
        "M_l": estado.M_l,
        "M_s": estado.M_s,
        "delta": estado.delta_promedio,
        "coherente": estado.coherente,
        "nodos_fragiles": estado.nodos_fragiles,
        "nodos": [
            {
                "id": n.nodo_id,
                "m": n.dimension_m,
                "l": n.dimension_l,
                "s": n.dimension_s,
                "delta": n.delta,
                "fragil": n.fragil,
                "tendencia_m": n.tendencia_m.value,
                "tendencia_l": n.tendencia_l.value,
                "tendencia_s": n.tendencia_s.value,
            }
            for n in estado.nodos
        ],
        "operaciones": [
            {
                "codigo": o.codigo,
                "nombre": o.nombre,
                "intensidad": o.intensidad,
                "nodos": o.nodos_implicados,
            }
            for o in operaciones
        ],
    }


@router.get("/daily")
async def api_daily(sociedad: str = Query("Chile")):
    informe = orch.ciclo_diario(sociedad)
    return {
        "fecha": informe.fecha.isoformat(),
        "resumen": informe.resumen_ejecutivo,
        "panorama": informe.panorama,
        "dinamicas": informe.dinamicas,
        "especulaciones_y_estudios": informe.especulaciones_y_estudios,
        "alertas": [{"tipo": a.tipo.value, "mensaje": a.mensaje} for a in informe.alertas],
        "mirada_adelante": informe.mirada_adelante,
        "dashboard": informe.dashboard.model_dump(),
    }


@router.get("/state")
async def api_state(sociedad: str = Query("Chile")):
    estado = store.cargar_estado(sociedad)
    if estado is None:
        return {"error": "No hay datos"}
    return estado.model_dump(mode="json")


@router.get("/history")
async def api_history(sociedad: str = Query("Chile")):
    fechas = store.listar_estados(sociedad)
    estados = []
    for f in fechas[-14:]:
        e = store.cargar_estado(sociedad, f)
        if e:
            estados.append({
                "fecha": f,
                "delta": e.delta_promedio,
                "M_m": e.M_m,
                "M_l": e.M_l,
                "M_s": e.M_s,
            })
    return {"sociedad": sociedad, "historial": estados}
