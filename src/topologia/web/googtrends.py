from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any

from topologia.models.llm import LLMClient


PROMPT_ANALISIS = """Eres un analista de tendencias para el sistema Topología.
Analiza la siguiente tendencia de Google: "{trend}"
Evalúa en orden:
1. ¿Es relevante para el estudio topológico de la cultura?
2. ¿Qué oportunidades de estudio topológico presenta?
3. ¿Puede mapearse a los 9 nodos culturales? (ECONOMIA, TRABAJO, CONTINUIDAD, POLITICA, LENGUAJE, ETICA_ESTETICA, TECNOLOGIA, EDUCACION, RELIGION)

Responde ÚNICAMENTE con:
RELEVANCIA: <0.1-9.9>
JUSTIFICACIÓN: <análisis breve, máx 3 oraciones>
NODOS: <lista separada por comas>"""


class ResultadoTendencia:
    def __init__(self, keyword: str, relevancia: float, analisis: str, nodos: list[str]):
        self.keyword = keyword
        self.relevancia = relevancia
        self.analisis = analisis
        self.nodos = nodos


class AnalizadorTendencias:
    def __init__(self):
        self.llm = LLMClient()

    def analizar(self, keyword: str) -> ResultadoTendencia:
        prompt = PROMPT_ANALISIS.format(trend=keyword)
        try:
            texto = self.llm.generar(prompt, temperatura=0.3, max_tokens=512)
            relevancia_match = re.search(r"RELEVANCIA:\s*([\d.]+)", texto)
            just_match = re.search(r"JUSTIFICACI[OÓ]N:\s*(.+)", texto, re.DOTALL)
            nodos_match = re.search(r"NODOS:\s*(.+)", texto)
            relevancia = float(relevancia_match.group(1)) if relevancia_match else 5.0
            analisis = just_match.group(1).strip() if just_match else texto[:200]
            nodos_str = nodos_match.group(1).strip() if nodos_match else ""
            nodos = [n.strip() for n in nodos_str.split(",") if n.strip()] if nodos_str else []
            return ResultadoTendencia(keyword, relevancia, analisis, nodos)
        except Exception as e:
            return ResultadoTendencia(keyword, 0.0, f"Error: {e}", [])

    def reseña(self, keyword: str) -> str:
        prompt = f"""Eres un analista del sistema Topología.
Genera una reseña breve (2-3 párrafos) explicando la tendencia "{keyword}"
y por qué es relevante para el estudio topológico de la cultura.
Reseña:"""
        try:
            return self.llm.generar(prompt, temperatura=0.5, max_tokens=512)
        except Exception:
            return ""
