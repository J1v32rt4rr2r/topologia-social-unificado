from __future__ import annotations

import math

from topologia.agents.base import Agent
from topologia.logger import logger
from topologia.models.schemas import (
    ConfigAgente,
    EstadoCultural,
    EvaluacionNodo,
    VotoObservador,
)
from topologia.prompts import PromptLoader


class Arbitro(Agent):
    def __init__(self):
        super().__init__(ConfigAgente(
            nombre="Árbitro",
            prompt="",
            temperatura=0.3,
            modelo="deepseek-chat",
            max_tokens=2048,
        ))
        self.prompts = PromptLoader()

    def analizar(self, evaluaciones: list[EvaluacionNodo]) -> dict:
        for ev in evaluaciones:
            ev.tension_observacional = self._calcular_tension(ev)

        tension_promedio = 0.0
        if evaluaciones:
            tension_promedio = sum(
                ev.tension_observacional for ev in evaluaciones
            ) / len(evaluaciones)

        alertas = []
        sesgos = []

        for ev in evaluaciones:
            if ev.tension_observacional > 0.7:
                diag = self._diagnosticar_nodo(ev)
                alertas.append({
                    "nodo": ev.nodo_id,
                    "tension": ev.tension_observacional,
                    "diagnostico": diag,
                })

        # Detectar sesgos sistémicos entre pares de observadores
        pares_tension = self._detectar_sesgos_sistemicos(evaluaciones)
        for par, tension in pares_tension.items():
            if tension > 0.6:
                sesgos.append(
                    f"Tensión persistente {par}: {tension:.2f}. "
                    "Estos dos observadores disienten sistemáticamente."
                )

        return {
            "tension_promedio": round(tension_promedio, 3),
            "tensiones_por_nodo": [
                {
                    "nodo": ev.nodo_id,
                    "tension_observacional": ev.tension_observacional,
                    "pares_en_conflicto": self._pares_en_conflicto(ev),
                }
                for ev in evaluaciones
            ],
            "alertas": alertas,
            "sesgos_detectados": sesgos,
        }

    def _calcular_tension(self, nodo: EvaluacionNodo) -> float:
        votos = [
            nodo.votos.get(d, VotoObservador())
            for d in ("M_m", "M_l", "M_s")
        ]

        if not any(v.dimension for v in votos):
            return 0.0

        # (a) Tensión por confianza: discrepancia entre scores ponderada por confianza
        pares = [(0, 1), (1, 2), (0, 2)]
        t_confianza = 0.0
        for i, j in pares:
            diff = abs(votos[i].score - votos[j].score) / 9.8
            mc = min(votos[i].confianza, votos[j].confianza)
            t_confianza += diff * mc
        t_confianza /= 3

        # (b) Tensión por varianza de scores (δ entre observadores)
        scores = [v.score for v in votos]
        media = sum(scores) / 3
        var = sum((s - media) ** 2 for s in scores) / 3
        t_score = math.sqrt(var) / 4.0

        # (c) Tensión declarada: conflictos explícitos entre dimensiones
        pares_conflicto = set()
        for v in votos:
            for target in v.tension_con:
                pares_conflicto.add((v.dimension, target))
        t_declarada = len(pares_conflicto) / 6.0

        # Tensor final
        return round(
            0.2 * t_score + 0.3 * t_confianza + 0.5 * t_declarada,
            3,
        )

    def _pares_en_conflicto(self, nodo: EvaluacionNodo) -> list[list[str]]:
        pares = []
        votos = nodo.votos
        dims = ["M_m", "M_l", "M_s"]
        for i, d1 in enumerate(dims):
            for d2 in dims[i + 1:]:
                v1 = votos.get(d1, VotoObservador())
                v2 = votos.get(d2, VotoObservador())
                if abs(v1.score - v2.score) > 2.0:
                    pares.append([d1, d2])
        return pares

    def _detectar_sesgos_sistemicos(
        self, evaluaciones: list[EvaluacionNodo]
    ) -> dict[str, float]:
        acum: dict[str, list[float]] = {
            "M_m_vs_M_l": [],
            "M_l_vs_M_s": [],
            "M_m_vs_M_s": [],
        }
        for ev in evaluaciones:
            v = ev.votos
            m = v.get("M_m", VotoObservador())
            l = v.get("M_l", VotoObservador())
            s = v.get("M_s", VotoObservador())
            acum["M_m_vs_M_l"].append(abs(m.score - l.score) / 9.8)
            acum["M_l_vs_M_s"].append(abs(l.score - s.score) / 9.8)
            acum["M_m_vs_M_s"].append(abs(m.score - s.score) / 9.8)
        return {
            par: round(sum(vals) / len(vals), 3) if vals else 0.0
            for par, vals in acum.items()
        }

    def _diagnosticar_nodo(self, nodo: EvaluacionNodo) -> str:
        v = nodo.votos
        m = v.get("M_m", VotoObservador())
        l = v.get("M_l", VotoObservador())
        s = v.get("M_s", VotoObservador())

        if abs(m.score - l.score) > abs(l.score - s.score) and abs(m.score - l.score) > abs(m.score - s.score):
            return f"Divergencia M_m({m.score})/M_l({l.score}) domina. El cambio parece ideológico antes que material."
        if abs(l.score - s.score) > abs(m.score - l.score) and abs(l.score - s.score) > abs(m.score - s.score):
            return f"Divergencia M_l({l.score})/M_s({s.score}) domina. Acción colectiva sin respaldo valórico o viceversa."
        if abs(m.score - s.score) > abs(m.score - l.score) and abs(m.score - s.score) > abs(l.score - s.score):
            return f"Divergencia M_m({m.score})/M_s({s.score}) domina. Organización social desacoplada de la base material."

        return ""