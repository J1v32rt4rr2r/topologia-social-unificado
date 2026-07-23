from topologia.agents.base import Agent
from topologia.models.schemas import ConfigAgente, EvaluacionNodo, ItemInformativo, AnalisisDim
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
            max_tokens=1024,
        ))
        self.prompts = PromptLoader()

    def evaluar_nodo(self, nodo_id: str, items: list[ItemInformativo], score_anterior: float = 5.0, just_anterior: str = "") -> EvaluacionNodo:
        pregunta = NODOS_PREGUNTAS.get(nodo_id, "")
        items_str = self.formatear_items(items)
        prompt = self.prompts.load("estadista_evaluar",
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
            dimension_m=round(punt, 1),
            dimension_l=0.0,
            dimension_s=0.0,
            justificacion_m=just,
            tendencia_m=tend,
            score_anterior_m=score_anterior,
        )

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
            resultado = {
                "dimension": "M_m",
                "patron_id": kwargs.get("patron_id", "P-???"),
                "confianza": 0.0,
                "evidencia": f"Error: {e}",
                "hallazgo": "",
                "conclusion": "Error en investigación",
            }

        return AnalisisDim(**resultado)
