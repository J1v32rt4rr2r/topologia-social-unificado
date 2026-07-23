from topologia.agents.base import Agent
from topologia.models.schemas import ConfigAgente, EvaluacionNodo, ItemInformativo, AnalisisDim
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

    def evaluar_nodo(self, nodo_id: str, items: list[ItemInformativo], score_anterior: float = 5.0, just_anterior: str = "") -> EvaluacionNodo:
        pregunta = NODOS_PREGUNTAS.get(nodo_id, "")
        items_str = self.formatear_items(items)
        prompt = self.prompts.load("filosofo_evaluar",
            nodo=nodo_id,
            pregunta_nodo=pregunta,
            items_del_nodo=items_str,
            score_anterior=score_anterior,
            justificacion_anterior=just_anterior,
        )
        try:
            resultado = self.ejecutar_prompt(prompt, formato_json=True)
            punt = max(0.1, min(9.9, float(resultado.get("puntuacion", 5.0))))
            just = resultado.get("justificacion", "")
            tend = resultado.get("tendencia", "estable")
        except Exception:
            punt = 5.0
            just = "Error en evaluación"
            tend = "estable"

        return EvaluacionNodo(
            nodo_id=nodo_id,
            nodo_nombre=nodo_id.capitalize(),
            dimension_m=0.0,
            dimension_l=round(punt, 1),
            dimension_s=0.0,
            justificacion_l=just,
            tendencia_l=tend,
            score_anterior_l=score_anterior,
        )

    def validar_estudio(self, items_investigacion: list[ItemInformativo], **kwargs) -> AnalisisDim:
        prompt = self.prompts.load("filosofo_validar",
            patron_id=kwargs.get("patron_id", "P-???"),
            forma_patron=kwargs.get("forma_patron", ""),
            significado_patron=kwargs.get("significado_patron", ""),
            items_originales=kwargs.get("items_originales", ""),
            argumento_artista=kwargs.get("argumento_artista", ""),
            confianza_artista=kwargs.get("confianza_artista", "0.5"),
            items_investigacion=self.formatear_items(items_investigacion),
        )
        try:
            resultado = self.ejecutar_prompt(prompt, formato_json=True)
        except Exception:
            resultado = {
                "dimension": "M_l",
                "patron_id": kwargs.get("patron_id", "P-???"),
                "confirmado": False,
                "confianza": 0.0,
                "evidencia": "Error en validación",
                "contraevidencia": "",
                "posibilidad": "",
                "realidad": "",
                "conclusion": "Error",
            }
        return AnalisisDim(**resultado)
