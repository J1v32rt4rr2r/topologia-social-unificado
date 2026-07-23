from pydantic import BaseModel


OPERACIONES_CINETICAS: dict[str, dict] = {
    "O1a": {
        "nombre": "Separación horizontal pasiva",
        "forma": "Indiferencia entre nodos. Valores divergen sin conflicto explícito.",
        "significado": "La sociedad se fragmenta por desinterés, no por confrontación.",
    },
    "O1b": {
        "nombre": "Separación horizontal activa",
        "forma": "Nodos opuestos con tensión creciente. Deltas altos entre pares.",
        "significado": "Depredación entre grupos. Uno avanza a costa de otro.",
    },
    "O2": {
        "nombre": "Espiral convergente",
        "forma": "Nodos opuestos se acercan. Fusión de dimensiones.",
        "significado": "Los opuestos se reconcilian en un nuevo síntesis.",
    },
    "O3a": {
        "nombre": "Vertical devocional",
        "forma": "Un nodo muy alto, otro muy bajo. Distancia sacra.",
        "significado": "Sacralización de una esfera. Distancia reverencial.",
    },
    "O3b": {
        "nombre": "Vertical celebratorio",
        "forma": "Nodos alineados en alta puntuación. Tensión cero.",
        "significado": "Euforia colectiva. Armonía sin fricción.",
    },
    "O4a": {
        "nombre": "Cuadrícula centrada",
        "forma": "Nodos políticos con alta divergencia M_m vs M_l.",
        "significado": "Polarización. Discurso y realidad en direcciones opuestas.",
    },
    "O4b": {
        "nombre": "Cuadrícula doméstica",
        "forma": "Nodos estables con baja variación. Costumbrismo.",
        "significado": "La tradición como ancla. Resistencia al cambio.",
    },
    "O5": {
        "nombre": "Entropía geométrica",
        "forma": "Degradación generalizada en múltiples nodos.",
        "significado": "Descomposición sistémica. Pérdida de estructura.",
    },
    "O6": {
        "nombre": "Órbita parasitaria",
        "forma": "Asimetría persistente entre dos nodos. Dependencia.",
        "significado": "Un nodo vive a expensas de otro. Relación extractiva.",
    },
    "O7": {
        "nombre": "Reticular topológico",
        "forma": "El documento o archivo como estructura nodal.",
        "significado": "Lo escrito organiza lo real. El mapa es el territorio.",
    },
    "O8": {
        "nombre": "Válvula vertical",
        "forma": "Flujo controlado entre nodos. Regulación del acceso.",
        "significado": "Poder de filtro. Quién controla el paso entre esferas.",
    },
    "O9": {
        "nombre": "Escape horizontal",
        "forma": "Tecnología y discurso altos, sexualidad/reproducción baja.",
        "significado": "Fuga hacia lo digital. Repliegue del cuerpo y la reproducción. Desconexión somático-tecnológica.",
    },
    "O10": {
        "nombre": "Microderrota",
        "forma": "Inversión belleza-poder. Lo pequeño vence a lo grande.",
        "significado": "El débil se impone por astucia. Victoria menor.",
    },
    "O11": {
        "nombre": "Círculo expansivo",
        "forma": "Inclusión sin centro fijo. Expansión horizontal.",
        "significado": "Comunidad sin jerarquía. Red descentralizada.",
    },
    "O12": {
        "nombre": "Círculo de eliminación ritual",
        "forma": "Entropía ceremonial. Exclusión mediante ritual.",
        "significado": "El rito elimina sin violencia explícita.",
    },
    "O13": {
        "nombre": "Diagnóstico con deformación temporal reversible",
        "forma": "El nodo se evalúa con distorsión del tiempo.",
        "significado": "La memoria selectiva distorsiona el diagnóstico.",
    },
    "O14": {
        "nombre": "Transición de fase / Giroscopio autorreferente",
        "forma": "El sistema se observa a sí mismo. Cambio de fase.",
        "significado": "Autoobservación. El sistema cambia al medirse.",
    },
}


class OperacionCineticaCatalog(BaseModel):
    codigo: str
    nombre: str
    forma: str
    significado: str
    detectores: list[str] = []


def get_operacion(codigo: str) -> OperacionCineticaCatalog | None:
    if codigo not in OPERACIONES_CINETICAS:
        return None
    meta = OPERACIONES_CINETICAS[codigo]
    return OperacionCineticaCatalog(
        codigo=codigo,
        nombre=meta["nombre"],
        forma=meta["forma"],
        significado=meta["significado"],
    )


def listar_operaciones() -> list[OperacionCineticaCatalog]:
    return [
        OperacionCineticaCatalog(codigo=c, **m)
        for c, m in OPERACIONES_CINETICAS.items()
    ]
