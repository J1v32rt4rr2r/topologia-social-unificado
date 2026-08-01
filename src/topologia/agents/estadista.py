from topologia.agents.base import Agent
from topologia.logger import logger
from topologia.models.schemas import (
    ConfigAgente, EvaluacionNodo, ItemInformativo, AnalisisDim, VotoObservador,
)
from topologia.prompts import PromptLoader


NODOS_PREGUNTAS = {
    "ECONOMIA": "¿Qué recursos materiales existen y cómo están distribuidos?",
    "TRABAJO": "¿Qué herramientas y tecnología productiva existen?",
    "SEXUALIDAD": "¿Qué recursos de salud sexual, anticoncepción, educación sexual y regulación reproductiva existen?",
    "POLITICA": "¿Qué instituciones y edificios gubernamentales existen?",
    "LENGUAJE": "¿Qué soportes físicos de escritura y bibliotecas existen?",
    "ETICA_ESTETICA": "¿Qué obras de arte, monumentos y objetos rituales existen?",
    "TECNOLOGIA": "¿Qué máquinas, herramientas e infraestructura técnica existen?",
    "EDUCACION": "¿Qué escuelas, universidades y recursos pedagógicos existen?",
    "RELIGION": "¿Qué símbolos, textos dogmáticos, propaganda ideológica y objetos de culto existen?",
}


class Estadista(Agent):
    def __init__(self):
        super().__init__(ConfigAgente(
            nombre="Estadista",
            prompt="",
            temperatura=0.4,
            modelo="deepseek-chat",
            max_tokens=2048,
        ))
        self.prompts = PromptLoader()

    def evaluar_nodo(
        self,
        nodo_id: str,
        items: list[ItemInformativo],
        score_anterior: float = 5.0,
        just_anterior: str = "",
        puntuacion_m_l: float | None = None,
        justificacion_m_l: str = "",
        puntuacion_m_s: float | None = None,
        justificacion_m_s: str = "",
    ) -> VotoObservador:
        pregunta = NODOS_PREGUNTAS.get(nodo_id, "")
        items_str = self.formatear_items(items)
        prompt = self.prompts.load("estadista_evaluar",
            nodo=nodo_id,
            pregunta_nodo=pregunta,
            items_del_nodo=items_str,
            score_anterior=score_anterior,
            justificacion_anterior=just_anterior,
            puntuacion_m_l=puntuacion_m_l if puntuacion_m_l is not None else "aún no evaluado",
            justificacion_m_l=justificacion_m_l or "aún no disponible",
            puntuacion_m_s=puntuacion_m_s if puntuacion_m_s is not None else "aún no evaluado",
            justificacion_m_s=justificacion_m_s or "aún no disponible",
        )
        try:
            resultado = self.ejecutar_prompt(prompt, formato_json=True)
            if isinstance(resultado, list):
                resultado = resultado[0] if resultado else {}
            punt = max(0.1, min(9.9, float(resultado.get("puntuacion", 5.0))))
            just = resultado.get("justificacion", "")
            tend = resultado.get("tendencia", "estable")
            conf = float(resultado.get("confianza", 0.5))
            contra = resultado.get("contra_punto_inicial", "")
            tension_con = resultado.get("tension_con", [])
        except Exception as e:
            logger.warning(f"[{self.config.nombre}] fallback evaluar_nodo({nodo_id}): {e}")
            punt = 5.0
            just = "Error en evaluación"
            tend = "estable"
            conf = 0.0
            contra = ""
            tension_con = []

        return VotoObservador(
            dimension="M_m",
            score=round(punt, 1),
            justificacion=just,
            confianza=conf,
            tendencia=tend,
            contra_punto=contra,
            tension_con=tension_con,
        )

    def deliberar(
        self,
        nodo_id: str,
        mi_voto: VotoObservador,
        votos_otros: dict[str, VotoObservador],
    ) -> dict:
        prompt = self.prompts.load("estadista_deliberar",
            nodo=nodo_id,
            mi_score=mi_voto.score,
            mi_confianza=mi_voto.confianza,
            mi_justificacion=mi_voto.justificacion,
            score_m_l=votos_otros.get("M_l", VotoObservador()).score,
            confianza_m_l=votos_otros.get("M_l", VotoObservador()).confianza,
            justificacion_m_l=votos_otros.get("M_l", VotoObservador()).justificacion,
            score_m_s=votos_otros.get("M_s", VotoObservador()).score,
            confianza_m_s=votos_otros.get("M_s", VotoObservador()).confianza,
            justificacion_m_s=votos_otros.get("M_s", VotoObservador()).justificacion,
        )
        try:
            resultado = self.ejecutar_prompt(prompt, formato_json=True)
            if isinstance(resultado, list):
                resultado = resultado[0] if resultado else {}
            return {
                "ajuste": float(resultado.get("ajuste_puntuacion", 0.0)),
                "mantiene": bool(resultado.get("mantiene", True)),
                "justificacion": resultado.get("justificacion_ajuste", ""),
                "contra_punto": resultado.get("contra_punto", ""),
                "tension_con": resultado.get("tension_con", []),
                "nueva_confianza": float(resultado.get("nueva_confianza", mi_voto.confianza)),
                "reflexion": resultado.get("reflexion", ""),
            }
        except Exception as e:
            logger.warning(f"[{self.config.nombre}] fallback deliberar({nodo_id}): {e}")
            return {
                "ajuste": 0.0,
                "mantiene": True,
                "justificacion": "Error en deliberación",
                "contra_punto": "",
                "tension_con": [],
                "nueva_confianza": mi_voto.confianza,
                "reflexion": "",
            }

    def validar_estudio(self, items_investigacion: list[ItemInformativo], **kwargs) -> AnalisisDim:
        prompt = self.prompts.load("estadista_validar",
            patron_id=kwargs.get("patron_id", "P-???"),
            forma_patron=kwargs.get("forma_patron", ""),
            significado_patron=kwargs.get("significado_patron", ""),
            argumento_artista=kwargs.get("argumento_artista", ""),
            pregunta_abierta=kwargs.get("pregunta_abierta", ""),
            items_investigacion=self.formatear_items(items_investigacion),
        )
        try:
            resultado = self.ejecutar_prompt(prompt, formato_json=True)
        except Exception as e:
            logger.warning(f"[{self.config.nombre}] fallback validar_estudio: {e}")
            resultado = {
                "dimension": "M_m",
                "patron_id": kwargs.get("patron_id", "P-???"),
                "confianza": 0.0,
                "evidencia": f"Error: {e}",
                "hallazgo": "",
                "conclusion": "Error en investigación",
            }

        return AnalisisDim(**resultado)