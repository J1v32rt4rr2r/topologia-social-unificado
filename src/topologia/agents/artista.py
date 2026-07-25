from __future__ import annotations

import json
import re
from pathlib import Path

from topologia.agents.base import Agent
from topologia.logger import logger
from topologia.models.schemas import (
    ConfigAgente,
    Especulacion,
    EstadoCultural,
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

    def _formatear_estado_vectores(self, estado: EstadoCultural | None) -> str:
        if not estado:
            return ""
        lineas = [f"  M_m={estado.M_m}  M_l={estado.M_l}  M_s={estado.M_s}  delta={estado.delta_promedio}°"]
        for n in estado.nodos:
            m, l, s = n.dimension_m, n.dimension_l, n.dimension_s
            d = n.delta
            if abs(l - s) <= 0.5:
                clasif = "estructura ideologica consolidada"
            elif l > m and s > m:
                clasif = "anhelo insatisfecho"
            elif m > l and m > s:
                clasif = "materialidad dominante"
            else:
                clasif = ""
            lineas.append(f"  {n.nodo_id:15s} M_m={m}  M_l={l}  M_s={s}  delta={d:5.1f}°  [{clasif}]")
        return "\n".join(lineas)

    def _formatear_especulaciones_previas(self, estudios: list) -> str:
        if not estudios:
            return "No hay especulaciones anteriores registradas."
        lineas = []
        for e in estudios[-10:]:
            tag = "✅ VALIDADO" if not e.tension_latente and e.respuesta and e.respuesta != "Sin hallazgos concluyentes" else "🔍 ABIERTO" if e.tension_latente else "❌ SIN CONCLUSION"
            lineas.append(f"- {e.patron_id}: {e.pregunta_investigada or '(sin pregunta)'} → {tag}")
            lineas.append(f"  Hallazgo: {e.respuesta[:150]}")
        return "\n".join(lineas)

    def _formatear_historial(self, estados: list[EstadoCultural]) -> str:
        if not estados:
            return "No hay historial disponible."
        lineas = []
        for nodo_id in ["ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA", "LENGUAJE",
                         "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION"]:
            evol = []
            for e in estados:
                for n in e.nodos:
                    if n.nodo_id == nodo_id:
                        evol.append(f"δ={n.delta:.1f}")
                        break
            if evol:
                flecha = "↓" if len(estados) >= 2 and estados[-1].delta_promedio < estados[0].delta_promedio else "↑" if len(estados) >= 2 and estados[-1].delta_promedio > estados[0].delta_promedio else "→"
                lineas.append(f"  {nodo_id:15s} {flecha} {' → '.join(evol)}")
        return "\n".join(lineas)

    def especular(self, items: list[ItemInformativo], estado: EstadoCultural | None = None,
                  historial: list[EstadoCultural] | None = None,
                  estudios_previos: list | None = None) -> list[Especulacion]:
        patrones_str = self._formatear_patrones_memoria()
        items_str = self.formatear_items(items)
        vectores_str = self._formatear_estado_vectores(estado)
        historial_str = self._formatear_historial(historial or []) if historial else "No hay historial disponible."
        esp_previas_str = self._formatear_especulaciones_previas(estudios_previos or [])
        prompt = self.prompts.load("artista_noticias",
            patrones_en_memoria=patrones_str,
            estado_vectores=vectores_str,
            items_del_dia=items_str,
            datos_historicos=historial_str,
            especulaciones_previas=esp_previas_str,
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