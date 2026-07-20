from topologia.agents.base import Agent
from topologia.models.schemas import ConfigAgente, EvaluacionNodo, ItemInformativo, AnalisisDim
from topologia.prompts import PromptLoader


NODOS_PREGUNTAS = {
    "ECONOMIA": "¿Cómo se organizan las redes de producción, distribución y relaciones laborales?",
    "TRABAJO": "¿Cómo es la organización sindical y la división social del trabajo?",
    "CONTINUIDAD": "¿Cómo se transmiten los rituales intergeneracionales?",
    "POLITICA": "¿Cómo son las relaciones de poder, jerarquías y participación ciudadana?",
    "LENGUAJE": "¿Cómo se usa el lenguaje en la sociedad, dialectos y comunicación?",
    "ETICA_ESTETICA": "¿Cuáles son las normas compartidas, el gusto colectivo y el juicio social?",
    "TECNOLOGIA": "¿Cómo son las comunidades técnicas y la brecha digital?",
    "EDUCACION": "¿Cómo es el aprendizaje social, la mentoría y la transmisión oral?",
    "RELIGION": "¿Cómo es la polarización ideológica, el sectarismo y la adhesión a dogmas?",
}


class Sociologo(Agent):
    def __init__(self):
        super().__init__(ConfigAgente(
            nombre="Sociólogo",
            prompt="",
            temperatura=0.2,
            modelo="deepseek-chat",
            max_tokens=1024,
        ))
        self.prompts = PromptLoader()

    def evaluar_nodo(self, nodo_id: str, items: list[ItemInformativo], score_anterior: float = 5.0, just_anterior: str = "") -> EvaluacionNodo:
        pregunta = NODOS_PREGUNTAS.get(nodo_id, "")
        items_str = self.formatear_items(items)
        prompt = self.prompts.load("sociologo_evaluar",
            nodo=nodo_id,
            pregunta_nodo=pregunta,
            items_del_nodo=items_str,
            score_anterior=score_anterior,
            justificacion_anterior=just_anterior,
        )
        try:
            resultado = self.ejecutar_prompt(prompt, formato_json=True)
            punt = float(resultado.get("puntuacion", 5.0))
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
            dimension_l=0.0,
            dimension_s=round(punt, 1),
            justificacion_s=just,
            tendencia_s=tend,
            score_anterior_s=score_anterior,
        )

    def validar_estudio(self, items_investigacion: list[ItemInformativo], **kwargs) -> AnalisisDim:
        prompt = self.prompts.load("sociologo_validar",
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
                "dimension": "M_s",
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
