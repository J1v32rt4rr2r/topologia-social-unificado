from topologia.agents.base import Agent
from topologia.models.schemas import ConfigAgente, EvaluacionNodo, ItemInformativo, AnalisisDim


PROMPT_EVALUAR = """Eres el Estadista, evaluador de la DIMENSIÓN MATERIAL en el sistema Topología.
Mides: infraestructura, recursos físicos, capacidad productiva, bienes tangibles.

Hoy evaluamos el nodo: {nodo}
(del total de 9 nodos culturales: ECONOMIA, TRABAJO, CONTINUIDAD, POLITICA, LENGUAJE, ETICA_ESTETICA, TECNOLOGIA, EDUCACION, RELIGION)

Pregunta guía para este nodo: {pregunta_nodo}

NOTICIAS RELEVANTES PARA EVALUAR ESTE NODO:
{items_del_nodo}

Puntuación anterior de este nodo: {score_anterior}
Justificación anterior: {justificacion_anterior}

INSTRUCCIONES:
1. Analiza las noticias y determina el estado actual de la dimensión material en este nodo cultural.
2. Asigna un puntaje del 0.1 al 9.9 (0.1 = mínimo, 9.9 = máximo).
3. Justifica tu puntuación en 1-2 oraciones citando evidencia concreta.
4. Señala si hay un cambio significativo respecto a la puntuación anterior.

FORMATO DE RESPUESTA (JSON):
{{
  "nodo": "{nodo}",
  "dimension": "M_m",
  "puntuacion": 7.2,
  "justificacion": "Los recursos materiales del nodo se mantienen estables pero con señales de deterioro en infraestructura...",
  "tendencia": "estable | mejora | deterioro",
  "senal_temprana": "Opcional: alguna señal sutil que podría ser relevante pero no alcanza a afectar la puntuación"
}}"""


PROMPT_VALIDAR = """Eres el Estadista, especialista en la DIMENSIÓN MATERIAL.

El Artista ha hecho una ESPECULACIÓN que requiere validación técnica:

ESPECULACIÓN:
- Patrón sugerido: {patron_id} — {forma_patron}
- Significado del patrón: {significado_patron}
- Noticias donde se detectó: {items_originales}
- Argumento del Artista: {argumento_artista}
- Confianza declarada: {confianza_artista}

INVESTIGACIÓN ADICIONAL REALIZADA:
Se recopilaron más fuentes sobre el tema:
{items_investigacion}

INSTRUCCIONES:
1. Analiza tanto las noticias originales como la investigación adicional.
2. Determina si desde tu dimensión (MATERIAL) el patrón se confirma:

   Para la FORMA del patrón:
   - ¿Los datos concretos respaldan la estructura que el Artista percibe?
   - ¿Hay evidencia mensurable que coincida?

   Para el SIGNIFICADO del patrón:
   - ¿El contexto valórico o narrativo respalda la interpretación del Artista?
   - ¿Hay discursos, valores o narrativas que coincidan?

3. Produce tu veredicto para esta dimensión.

FORMATO DE RESPUESTA (JSON):
{{
  "dimension": "M_m",
  "patron_id": "{patron_id}",
  "confirmado": true,
  "confianza": 0.75,
  "evidencia": "Los datos de producción minera muestran una caída del 12% consistente con la 'caída vertical' del patrón...",
  "contraevidencia": "El factor externo (precio internacional del cobre) explica la caída sin necesidad del patrón propuesto.",
  "conclusion": "La forma del patrón se observa parcialmente. El significado no puede confirmarse con los datos disponibles."
}}

REGLAS:
- confirmado debe ser true SOLO si la evidencia es sólida.
- confianza refleja tu seguridad en la conclusión (0.0-1.0).
- contraevidencia es tan importante como la evidencia.
- Si no hay suficiente información, di 'insuficiente' en conclusion.
- No te dejes influir por la confianza declarada del Artista."""


NODOS_PREGUNTAS = {
    "ECONOMIA": "¿Qué recursos materiales existen y cómo están distribuidos?",
    "TRABAJO": "¿Qué herramientas y tecnología productiva existen?",
    "CONTINUIDAD": "¿Qué archivos, monumentos y patrimonio material se conservan?",
    "POLITICA": "¿Qué instituciones y edificios gubernamentales existen?",
    "LENGUAJE": "¿Qué soportes físicos de escritura y bibliotecas existen?",
    "ETICA_ESTETICA": "¿Qué obras de arte, monumentos y objetos rituales existen?",
    "TECNOLOGIA": "¿Qué máquinas, herramientas e infraestructura técnica existen?",
    "EDUCACION": "¿Qué escuelas, universidades y recursos pedagógicos existen?",
    "RELIGION": "¿Qué templos, iglesias y objetos sagrados existen?",
}


class Estadista(Agent):
    def __init__(self):
        super().__init__(ConfigAgente(
            nombre="Estadista",
            prompt="",
            temperatura=0.2,
            modelo="deepseek-chat",
            max_tokens=1024,
        ))

    def evaluar_nodo(self, nodo_id: str, items: list[ItemInformativo], score_anterior: float = 5.0, just_anterior: str = "") -> EvaluacionNodo:
        pregunta = NODOS_PREGUNTAS.get(nodo_id, "")
        items_str = self.formatear_items(items)
        prompt = PROMPT_EVALUAR.format(
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
            dimension_m=round(punt, 1),
            dimension_l=0.0,
            dimension_s=0.0,
            justificacion_m=just,
            tendencia_m=tend,
            score_anterior_m=score_anterior,
        )

    def validar_estudio(self, items_investigacion: list[ItemInformativo], **kwargs) -> AnalisisDim:
        prompt = PROMPT_VALIDAR.format(
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
        except Exception as e:
            resultado = {
                "dimension": "M_m",
                "patron_id": kwargs.get("patron_id", "P-???"),
                "confirmado": False,
                "confianza": 0.0,
                "evidencia": f"Error: {e}",
                "contraevidencia": "",
                "conclusion": "Error en validación",
            }

        return AnalisisDim(**resultado)
