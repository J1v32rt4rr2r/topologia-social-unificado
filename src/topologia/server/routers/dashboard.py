from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from topologia.math.operations import detectar_operaciones
from topologia.orchestrator import Orchestrator
from topologia.storage.store import FileStore

router = APIRouter()

base = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base / "frontend" / "templates"))
orch = Orchestrator()
store = FileStore()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")


@router.get("/api/dashboard/data")
async def dashboard_data(sociedad: str = "Chile"):
    estado = store.cargar_estado(sociedad)
    if estado is None:
        return {"error": "No hay datos"}

    operaciones = detectar_operaciones(estado)
    fechas = store.listar_estados(sociedad)
    historial = []
    for f in fechas[-14:]:
        e = store.cargar_estado(sociedad, f)
        if e:
            historial.append({
                "fecha": f,
                "delta": e.delta_promedio,
                "M_m": e.M_m,
                "M_l": e.M_l,
                "M_s": e.M_s,
            })

    return {
        "sociedad": estado.sociedad,
        "fecha": estado.fecha.isoformat(),
        "delta_promedio": estado.delta_promedio,
        "coherente": estado.coherente,
        "M_m": estado.M_m,
        "M_l": estado.M_l,
        "M_s": estado.M_s,
        "nodos": [
            {
                "id": n.nodo_id,
                "m": n.dimension_m,
                "l": n.dimension_l,
                "s": n.dimension_s,
                "delta": n.delta,
                "fragil": n.fragil,
                "just_m": n.justificacion_m,
                "just_l": n.justificacion_l,
                "just_s": n.justificacion_s,
                "tend_m": n.tendencia_m,
                "tend_l": n.tendencia_l,
                "tend_s": n.tendencia_s,
            }
            for n in estado.nodos
        ],
        "operaciones": [
            {
                "codigo": o.codigo,
                "nombre": o.nombre,
                "intensidad": o.intensidad,
                "nodos": o.nodos_implicados,
                "descripcion": o.descripcion,
            }
            for o in operaciones
        ],
        "historial": historial,
    }
