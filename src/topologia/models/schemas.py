from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class EstadoPatron(str, Enum):
    especulativo = "especulativo"
    en_estudio = "en_estudio"
    validado = "validado"
    refutado = "refutado"
    parcial = "parcial"


class TipoAlerta(str, Enum):
    reconfiguracion = "reconfiguracion"
    cambio_acelerado = "cambio_acelerado"
    riesgo_estructural = "riesgo_estructural"


class TendenciaDim(str, Enum):
    estable = "estable"
    mejora = "mejora"
    deterioro = "deterioro"


# ─── Capa 1: ESTRUCTURAL ───────────────────────────────────


class EvaluacionNodo(BaseModel):
    nodo_id: str
    nodo_nombre: str
    dimension_m: float = Field(ge=0.0, le=9.9)
    dimension_l: float = Field(ge=0.0, le=9.9)
    dimension_s: float = Field(ge=0.0, le=9.9)
    justificacion_m: str = ""
    justificacion_l: str = ""
    justificacion_s: str = ""
    delta: float = 0.0
    fragil: bool = False
    tendencia_m: TendenciaDim = TendenciaDim.estable
    tendencia_l: TendenciaDim = TendenciaDim.estable
    tendencia_s: TendenciaDim = TendenciaDim.estable
    score_anterior_m: float | None = None
    score_anterior_l: float | None = None
    score_anterior_s: float | None = None

    def toroidal_angles(self) -> tuple[float, float, float]:
        theta_m = 360.0 / max(self.dimension_m, 0.1)
        theta_l = 360.0 / max(self.dimension_l, 0.1)
        theta_s = 360.0 / max(self.dimension_s, 0.1)
        return (theta_m, theta_l, theta_s)


class EstadoCultural(BaseModel):
    sociedad: str = "Chile"
    nivel_fractal: int = 1
    fecha: datetime = Field(default_factory=datetime.now)
    M_m: float = 0.0
    M_l: float = 0.0
    M_s: float = 0.0
    delta_promedio: float = 0.0
    coherente: bool = True
    nodos: list[EvaluacionNodo] = []
    nodos_fragiles: list[str] = []
    era_k: int = 1
    theta_cultura: float = 0.0
    tension_total: float = 0.0
    vuelco_detectado: bool = False

    # Formas culturales complejas (e^(2πi / m), m = Σ(v/9.9))
    m_m: float = 0.0
    m_l: float = 0.0
    m_s: float = 0.0
    theta_m: float = 0.0  # grados
    theta_l: float = 0.0  # grados
    theta_s: float = 0.0  # grados
    coherencia_interna: float = 0.0  # Δθ promedio entre las 3 formas (grados)


# ─── Capa 2: CINÉTICA ──────────────────────────────────────


class OperacionCinetica(BaseModel):
    codigo: str
    nombre: str
    intensidad: float = Field(ge=0.0, le=1.0)
    nodos_implicados: list[str] = []
    descripcion: str = ""
    evidencia: str = ""


# ─── Capa 3: ESTUDIO ───────────────────────────────────────


class Especulacion(BaseModel):
    id: str = ""
    patron_id: str
    items_relacionados: list[str] = []
    confianza: float = Field(ge=0.0, le=1.0)
    argumento: str
    nodos_sugeridos: list[str] = []
    pregunta_abierta: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


class AnalisisDim(BaseModel):
    dimension: str
    patron_id: str
    confirmado: bool = False
    confianza: float = Field(default=0.0, ge=0.0, le=1.0)
    evidencia: str = ""
    contraevidencia: str = ""
    posibilidad: str = ""
    realidad: str = ""
    conclusion: str = ""


class Estudio(BaseModel):
    id: str = ""
    especulacion_id: str
    patron_id: str
    estado: EstadoPatron = EstadoPatron.en_estudio
    items_originales: list[str] = []
    items_investigacion: list[str] = []
    analisis: dict[str, AnalisisDim] = {}
    veredicto: str = ""
    informe_path: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


# ─── Capa 3b: PATRONES ─────────────────────────────────────


class PatronAnalogico(BaseModel):
    id: str
    forma: str
    significado: str
    origen_poetico: str = ""
    estado: EstadoPatron = EstadoPatron.especulativo
    descubierto_en: datetime = Field(default_factory=datetime.now)
    validado_en: datetime | None = None
    veces_estudiado: int = 0
    veces_validado: int = 0


# ─── Capa 4: NARRATIVA ─────────────────────────────────────


class Alerta(BaseModel):
    tipo: TipoAlerta
    mensaje: str


class DashboardData(BaseModel):
    metrica_principal: str = ""
    cambio_clave: str = ""
    nodos_criticos: list[str] = []
    patrones_nuevos: list[str] = []


class InformeDiario(BaseModel):
    fecha: datetime = Field(default_factory=datetime.now)
    panorama: str = ""
    dinamicas: str = ""
    especulaciones_y_estudios: str = ""
    alertas: list[Alerta] = []
    mirada_adelante: str = ""
    resumen_ejecutivo: str = ""
    dashboard: DashboardData = Field(default_factory=DashboardData)


# ─── APRENDIZAJE ───────────────────────────────────────────


class RendimientoFuente(BaseModel):
    total_items: int = 0
    items_por_nodo: dict[str, int] = {}
    proporcion_relevantes: float = 0.0


class EstrategiaRecoleccion(BaseModel):
    sociedad: str = "Chile"
    generada_en: datetime = Field(default_factory=datetime.now)

    nodos_prioritarios: list[str] = []
    nodos_con_brecha: list[str] = []
    dimensiones_inestables: dict[str, str] = {}

    queries_generadas: dict[str, list[str]] = {}

    fuentes_activas: list[str] = []
    fuentes_ruidosas: list[str] = []
    peso_por_fuente: dict[str, float] = {}

    umbral_relevancia: float = 0.5
    max_items_por_nodo: int = 10


class ItemScored(BaseModel):
    item: ItemInformativo
    score: float = 0.0
    nodo_asignado: str = ""


# ─── UTILIDAD ──────────────────────────────────────────────


class ItemInformativo(BaseModel):
    id: str
    titulo: str
    fuente: str
    contenido: str
    url: str = ""
    fecha: datetime = Field(default_factory=datetime.now)
    tags: list[str] = []
    nodo_sugerido: str = ""


class ConfigAgente(BaseModel):
    nombre: str
    prompt: str
    temperatura: float = 0.2
    modelo: str = "deepseek-chat"
    max_tokens: int = 1024
