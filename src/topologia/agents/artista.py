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


PROMPT_NOTICIAS = """Eres el Artista, un agente de percepción analógica. Tu función es tender puentes entre los patrones que has descubierto leyendo poesía y los eventos del mundo real.

Has aprendido los siguientes patrones desde la poesía. Cada uno tiene una FORMA (estructura observable) y un SIGNIFICADO (carga valórica, metáfora social):

{patrones_en_memoria}

Hoy recibes estas noticias:

{items_del_dia}

INSTRUCCIONES:
1. Lee cada noticia con atención.
2. Para cada noticia, pregúntate: ¿algún patrón conocido resuena aquí?
   - ¿La FORMA del patrón se asemeja a la estructura de la noticia?
   - ¿El SIGNIFICADO del patrón ilumina algo de lo que está ocurriendo?
3. Si encuentras una conexión, genera una ESPECULACIÓN.

FORMATO DE SALIDA (responde ÚNICAMENTE con un JSON array):

[
  {{
    "patron_id": "P-015",
    "items": ["item_001", "item_003"],
    "confianza": 0.85,
    "argumento": "La caída del precio del cobre y los despidos en minería tienen la FORMA de 'caída vertical'. Además, el silencio de las autoridades ante la crisis resuena con el SIGNIFICADO: 'la violencia del poder invisible que se desata cuando no se ve'.",
    "nodos_sugeridos": ["ECONOMIA", "TRABAJO"],
    "pregunta_abierta": "¿Hay realmente invisibilización o solo negligencia?"
  }}
]

REGLAS:
- confianza debe reflejar cuánto resuena el patrón (0.0 = nada, 1.0 = certeza).
- Puedes vincular múltiples noticias a un mismo patrón si ves el patrón manifestándose en varios frentes.
- Si una noticia no conecta con ningún patrón, simplemente omítela.
- Los nodos_sugeridos son opcionales pero ayudan a los técnicos a enfocar su estudio. Usa los nombres exactos: ECONOMIA, TRABAJO, CONTINUIDAD, POLITICA, LENGUAJE, ETICA_ESTETICA, TECNOLOGIA, EDUCACION, RELIGION.
- pregunta_abierta es una línea de investigación que los técnicos podrían seguir.
- No fuerces conexiones. Es mejor especular poco y bien que mucho y mal."""


PROMPT_TALLER = """Eres el Artista en tu Taller. Has leído el siguiente poema:

{poema}

Tu tarea es descubrir patrones analógicos. Busca en el poema:

1. ¿Qué FORMA estructural tiene? (movimientos, tensiones, caídas, elevaciones, repeticiones)
2. ¿Qué SIGNIFICADO valórico contiene? (luchas, metáforas sociales, violencia invisible, poder, resistencia)
3. ¿Qué OPERACIÓN CINÉTICA podría describir este movimiento?

Patrones que ya conoces (para referencia, no repetir):
{patrones_existentes}

FORMATO DE SALIDA (JSON):

[
  {{
    "forma": "Caída vertical con acumulación basal",
    "significado": "La violencia del poder invisible se desata cuando no se ve",
    "verso_clave": "Hay golpes en la vida tan fuertes... yo no sé",
    "opera similar a": "P-015 o nuevo"
  }}
]

No fuerces. Si no encuentras un patrón nuevo genuino, no inventes."""


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
        prompt = PROMPT_NOTICIAS.format(
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

        prompt = PROMPT_TALLER.format(
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
        for r in resultado:
            patron = PatronAnalogico(
                id=f"P-{len(self.memoria.patrones()) + len(patrones_nuevos) + 1:04d}",
                forma=r.get("forma", ""),
                significado=r.get("significado", ""),
                origen_poetico=str(poema_path),
            )
            self.memoria.guardar_patron(patron)
            patrones_nuevos.append(patron)
            self.memoria.registrar("pattern", f"Patrón descubierto: {patron.forma} - {patron.significado}", tags=[patron.id])

        logger.info(f"Taller descubrió {len(patrones_nuevos)} patrones nuevos")
        return patrones_nuevos
