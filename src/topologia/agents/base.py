from __future__ import annotations

from typing import Any

from topologia.logger import logger
from topologia.models.llm import LLMClient
from topologia.models.schemas import ConfigAgente, ItemInformativo


def _fecha_item(item: ItemInformativo) -> str:
    """Fecha de publicación del item; 'no disponible' si no se conoce."""
    if "sin_fecha" in item.tags:
        return "no disponible"
    try:
        return item.fecha.strftime("%d/%m/%Y")
    except Exception:
        return "no disponible"


class Agent:
    def __init__(self, config: ConfigAgente):
        self.config = config
        self.llm = LLMClient()

    def ejecutar_prompt(self, prompt: str, formato_json: bool = False) -> str | dict | Any:
        logger.info(f"[{self.config.nombre}] generando respuesta...")
        if formato_json:
            return self.llm.generar_json(prompt, self.config.temperatura, self.config.max_tokens)
        return self.llm.generar(prompt, self.config.temperatura, self.config.max_tokens)

    def formatear_items(self, items: list[ItemInformativo]) -> str:
        if not items:
            return "No hay información disponible."
        partes = []
        for i, item in enumerate(items[:15]):
            fecha = _fecha_item(item)
            partes.append(f"[{i+1}] {item.titulo}\n   Fecha: {fecha}\n   Fuente: {item.fuente}\n   {item.contenido[:300]}")
        return "\n\n".join(partes)
