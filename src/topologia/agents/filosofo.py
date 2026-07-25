from topologia.agents.base import Agent
from topologia.models.schemas import (
    ConfigAgente, EvaluacionNodo, ItemInformativo, AnalisisDim, VotoObservador,
)
from topologia.prompts import PromptLoader


NODOS_PREGUNTAS = {
    "ECONOMIA": "¿Qué ideología de mercado y teoría del valor predominan?",
    "TRABAJO": "¿Qué ética del trabajo y concepto de mérito existen?",
    "SEXUALIDAD": "¿Qué cosmovisiones, tabúes, morales sexuales y bioéticas predominan?",
    "POLITICA": "¿Qué filosofía política, leyes y constitución?",
    "LENGUAJE": "¿Qué gramática, lógica formal, semántica y discurso?",
    "ETICA_ESTETICA": "¿Qué principios éticos, cánones estéticos y moral?",
    "TECNOLOGIA": "¿Qué racionalidad tecnológica y episteme?",
    "EDUCACION": "¿Qué filosofía educativa, currículo y conocimiento valorado?",
    "RELIGION": "¿Qué dogmas, ideologías, principios incuestionables y sistemas de creencias?",
}


class Filosofo(Agent):
    def __init__(self):
        super().__init__(ConfigAgente(
            nombre="Filósofo",
            prompt="",
            temperatura=0.4,
            modelo="deepseek-chat",
            max_tokens=1024,
        ))
        self.prompts = PromptLoader()

    def evaluar_nodo(
        self,
        nodo_id: str,
        items: list[ItemInformativo],
        score_anterior: float = 5.0,
        just_anterior: str = "",
        puntuacion_m_m: float | None = None,
        justificacion_m_m: str = "",
        puntuacion_m_s: float | None = None,
        justificacion_m_s: str = "",
    ) -> VotoObservador:
        pregunta = NODOS_PREGUNTAS.get(nodo_id, "")
        items_str = self.formatear_items(items)
        prompt = self.prompts.load("filosofo_evaluar",
            nodo=nodo_id,
            pregunta_nodo=pregunta,
            items_del_nodo=items_str,
            score_anterior=score_anterior,
            justificacion_anterior=just_anterior,
            puntuacion_m_m=puntuacion_m_m if puntuacion_m_m is not None else "aún no evaluado",
            justificacion_m_m=justificacion_m_m or "aún no disponible",
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
        except Exception:
            punt = 5.0
            just = "Error en evaluación"
            tend = "estable"
            conf = 0.0
            contra = ""
            tension_con = []

        return VotoObservador(
            dimension="M_l",
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
        prompt = self.prompts.load("filosofo_deliberar",
            nodo=nodo_id,
            mi_score=mi_voto.score,
            mi_confianza=mi_voto.confianza,
            mi_justificacion=mi_voto.justificacion,
            score_m_m=votos_otros.get("M_m", VotoObservador()).score,
            confianza_m_m=votos_otros.get("M_m", VotoObservador()).confianza,
            justificacion_m_m=votos_otros.get("M_m", VotoObservador()).justificacion,
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
        except Exception:
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
        prompt = self.prompts.load("filosofo_validar",
            patron_id=kwargs.get("patron_id", "P-???"),
            forma_patron=kwargs.get("forma_patron", ""),
            significado_patron=kwargs.get("significado_patron", ""),
            argumento_artista=kwargs.get("argumento_artista", ""),
            pregunta_abierta=kwargs.get("pregunta_abierta", ""),
            items_investigacion=self.formatear_items(items_investigacion),
        )
        try:
            resultado = self.ejecutar_prompt(prompt, formato_json=True)
        except Exception:
            resultado = {
                "dimension": "M_l",
                "patron_id": kwargs.get("patron_id", "P-???"),
                "confianza": 0.0,
                "evidencia": "Error en investigación",
                "hallazgo": "",
                "conclusion": "Error",
            }
        return AnalisisDim(**resultado)