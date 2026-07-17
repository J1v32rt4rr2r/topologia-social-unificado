from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from topologia.agents.artista import Artista
from topologia.memoria.decisiones import DecisionDB

router = APIRouter()
artista = Artista()
memoria = DecisionDB()


class LearnRequest(BaseModel):
    ruta_poema: str


@router.post("/learn")
async def api_learn(req: LearnRequest):
    patrones = artista.taller(req.ruta_poema)
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
