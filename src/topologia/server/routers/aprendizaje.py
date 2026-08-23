from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from topologia.agents.artista import Artista
from topologia.memoria.decisiones import DecisionDB
from topologia.server.auth import requerir_api_key

router = APIRouter()
artista = Artista()
memoria = DecisionDB()

#: Raíz del repo (src/topologia/server/routers/ → parents[4]).
_REPO = Path(__file__).resolve().parents[4]
_DIR_POEMAS = _REPO / "data" / "poemas"


class LearnRequest(BaseModel):
    ruta_poema: str


def _sanitizar_ruta_poema(ruta: str) -> str:
    """Solo permite leer poemas dentro de data/poemas del repo.

    Impide que el endpoint lea archivos arbitrarios del sistema (el path
    se resuelve y debe quedar dentro del directorio de poemas).
    """
    p = Path(ruta).expanduser()
    p = (p if p.is_absolute() else _DIR_POEMAS / p).resolve()
    base = _DIR_POEMAS.resolve()
    if not p.is_relative_to(base):
        raise HTTPException(status_code=400, detail="ruta_poema debe estar dentro de data/poemas")
    if not p.is_file():
        raise HTTPException(status_code=404, detail="poema no encontrado")
    return str(p)


@router.post("/learn", dependencies=[Depends(requerir_api_key)])
def api_learn(req: LearnRequest):
    """Taller del Artista sobre un poema (lee archivos): requiere API key."""
    ruta = _sanitizar_ruta_poema(req.ruta_poema)
    patrones = artista.taller(ruta)
    return {
        "patrones": [
            {
                "id": p.id,
                "forma": p.forma,
                "significado": p.significado,
                "estado": p.estado.value,
                "origen": p.origen_poetico,
            }
            for p in patrones
        ],
        "total": len(patrones),
    }


@router.get("/patterns")
async def api_patterns():
    return {
        "patrones": [
            {
                "id": p.id,
                "forma": p.forma,
                "significado": p.significado,
                "estado": p.estado.value,
            }
            for p in memoria.patrones()
        ],
        "total": len(memoria.patrones()),
        "estadisticas": memoria.estadisticas(),
    }


@router.get("/speculations")
async def api_speculations():
    decisiones = memoria.listar(tipo="pattern")
    return {"especulaciones": decisiones[-20:]}
