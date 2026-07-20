from __future__ import annotations

import json
import re
from pathlib import Path

from topologia.agents.base import Agent
from topologia.logger import logger
from topologia.models.schemas import (
    ConfigAgente,
    Especulacion,
    ItemInformativo,
    PatronAnalogico,
)
from topologia.memoria.decisiones import DecisionDB
from topologia.memoria.bloques import BloquesMemoria
from topologia.prompts import PromptLoader


class Artista(Agent):
    def __init__(self):
        super().__init__(ConfigAgente(
            nombre="Artista",
            prompt="",
            temperatura=0.8,
            modelo="deepseek-chat",
            max_tokens=2048,
        ))
        self.memoria = DecisionDB()
        self.bloques = BloquesMemoria()
        self.prompts = PromptLoader()

    def _formatear_patrones_memoria(self) -> str:
        patrones = self.memoria.patrones()
        if not patrones:
            return "Aún no has descubierto patrones. Esta es tu primera vez."
        partes = []
        for p in patrones:
            estado = f"[{p.estado.value}]"
            partes.append(f"{p.id} {estado}: {p.forma}\n   Significado: {p.significado}")
        return "\n\n".join(partes)

    def especular(self, items: list[ItemInformativo]) -> list[Especulacion]:
        patrones_str = self._formatear_patrones_memoria()
        items_str = self.formatear_items(items)
        prompt = self.prompts.load("artista_noticias",
            patrones_en_memoria=patrones_str,
            items_del_dia=items_str,
        )
        try:
            resultado = self.ejecutar_prompt(prompt, formato_json=True)
        except Exception as e:
            logger.error(f"Error generando especulaciones: {e}")
            return []

        if isinstance(resultado, dict):
            resultado = [resultado]
        if not isinstance(resultado, list):
            return []

        especulaciones = []
        for i, r in enumerate(resultado):
            esp = Especulacion(
                id=f"ESP-{i+1:04d}",
                patron_id=r.get("patron_id", "P-???"),
                items_relacionados=r.get("items", []),
                confianza=float(r.get("confianza", 0.5)),
                argumento=r.get("argumento", ""),
                nodos_sugeridos=r.get("nodos_sugeridos", []),
                pregunta_abierta=r.get("pregunta_abierta", ""),
            )
            especulaciones.append(esp)
            self.memoria.registrar("pattern", f"Especulación: {esp.argumento}", tags=[esp.patron_id])

        logger.info(f"Artista generó {len(especulaciones)} especulaciones")
        return especulaciones

    def taller(self, ruta_poema: str) -> list[PatronAnalogico]:
        poema_path = Path(ruta_poema)
        if not poema_path.exists():
            logger.error(f"Poema no encontrado: {ruta_poema}")
            return []

        poema = poema_path.read_text(encoding="utf-8")
        patrones_str = self._formatear_patrones_memoria()

        prompt = self.prompts.load("artista_taller",
            poema=poema,
            patrones_existentes=patrones_str,
        )

        try:
            resultado = self.ejecutar_prompt(prompt, formato_json=True)
        except Exception as e:
            logger.error(f"Error en Taller: {e}")
            return []

        if isinstance(resultado, dict):
            resultado = [resultado]
        if not isinstance(resultado, list):
            return []

        patrones_nuevos = []
        existentes = self.memoria.patrones()
        max_id = 0
        for p in existentes:
            try:
                num = int(p.id.split("-")[1])
                if num > max_id:
                    max_id = num
            except (IndexError, ValueError):
                pass
        for r in resultado:
            patron = PatronAnalogico(
                id=f"P-{max_id + len(patrones_nuevos) + 1:04d}",
                forma=r.get("forma", ""),
                significado=r.get("significado", ""),
                origen_poetico=str(poema_path),
            )
            self.memoria.guardar_patron(patron)
            patrones_nuevos.append(patron)
            self.memoria.registrar("pattern", f"Patrón descubierto: {patron.forma} - {patron.significado}", tags=[patron.id])

        logger.info(f"Taller descubrió {len(patrones_nuevos)} patrones nuevos")
        return patrones_nuevos
