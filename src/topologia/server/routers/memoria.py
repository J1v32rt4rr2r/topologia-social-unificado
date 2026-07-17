from __future__ import annotations

from fastapi import APIRouter

from topologia.memoria.bloques import BloquesMemoria
from topologia.memoria.decisiones import DecisionDB

router = APIRouter()
memoria = DecisionDB()
bloques = BloquesMemoria()


@router.get("/decisions")
async def api_decisions(tipo: str | None = None, tag: str | None = None):
    return {"decisiones": memoria.listar(tipo=tipo, tag=tag)}


@router.get("/decisions/stats")
async def api_decisions_stats():
    return memoria.estadisticas()


@router.get("/blocks")
async def api_blocks():
    return {"bloques": bloques.listar(), "contenido": bloques.resumen()}


@router.get("/blocks/{nombre}")
async def api_block(nombre: str):
    contenido = bloques.leer(nombre)
    if not contenido:
        return {"error": "Bloque no encontrado"}
    return {"nombre": nombre, "contenido": contenido}
