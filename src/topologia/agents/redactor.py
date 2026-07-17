from topologia.agents.base import Agent
from topologia.logger import logger
from topologia.models.schemas import (
    Alerta,
    ConfigAgente,
    DashboardData,
    EstadoCultural,
    Estudio,
    Especulacion,
    InformeDiario,
    OperacionCinetica,
    TipoAlerta,
)


PROMPT_SINTESIS = """Eres el Redactor del sistema Topología. Tu función es tomar la producción completa del ciclo diario y transformarla en un relato claro, preciso y relevante.

Has recibido estos insumos del día de hoy:

## 1. ESTADO CULTURAL
{estado_cultural}

## 2. OPERACIONES CINÉTICAS DETECTADAS
{operaciones_activas}

## 3. ESPECULACIONES DEL ARTISTA
{especulaciones}

## 4. RESULTADOS DE ESTUDIOS
{estudios}

## 5. COMPARATIVA HISTÓRICA
{historial_reciente}

## 6. PROYECCIÓN
{proyeccion}

INSTRUCCIONES:
Genera un INFORME DIARIO estructurado con:

1. PANORAMA GENERAL (2-3 párrafos) - ¿Cuál es el estado cultural hoy? ¿Qué cambió respecto ayer? ¿Hay algo que amerite atención urgente?
2. DINÁMICAS DETECTADAS - ¿Qué operaciones cinéticas están activas y por qué importan?
3. ESPECULACIONES Y ESTUDIOS - ¿Qué vio el Artista hoy? ¿Qué estudios se hicieron y qué se encontró?
4. ALERTAS - Solo si aplica: δ > 45° (reconfiguración), Δδ > 5° (cambio acelerado), nodo frágil persistente
5. MIRADA HACIA ADELANTE - ¿Qué esperar? ¿Qué señales observar?

FORMATO DE SALIDA (JSON):
{{
  "fecha": "{fecha}",
  "panorama": "texto en markdown...",
  "dinamicas": "texto en markdown...",
  "especulaciones_y_estudios": "texto en markdown...",
  "alertas": [
    {{ "tipo": "reconfiguracion", "mensaje": "texto" }}
  ],
  "mirada_adelante": "texto...",
  "resumen_ejecutivo": "3 líneas que cualquiera pueda entender",
  "dashboard": {{
    "metrica_principal": "δ = X°",
    "cambio_clave": "lo más relevante del día",
    "nodos_criticos": ["nodo_id"],
    "patrones_nuevos": ["P-XXX"]
  }}
}}

REGLAS:
- No inventes información que no esté en los insumos.
- Traduce el lenguaje técnico pero sin perder precisión.
- El resumen_ejecutivo debe poder leerse en 10 segundos."""


class Redactor(Agent):
    def __init__(self):
        super().__init__(ConfigAgente(
            nombre="Redactor",
            prompt="",
            temperatura=0.5,
            modelo="deepseek-chat",
            max_tokens=2048,
        ))

    def sintetizar(
        self,
        estado: EstadoCultural,
        operaciones: list[OperacionCinetica],
        especulaciones: list[Especulacion],
        estudios: list[Estudio],
        historial: str = "",
        proyeccion: str = "",
    ) -> InformeDiario:
        estado_str = self._formatear_estado(estado)
        ops_str = self._formatear_operaciones(operaciones)
        esp_str = self._formatear_especulaciones(especulaciones)
        est_str = self._formatear_estudios(estudios)

        prompt = PROMPT_SINTESIS.format(
            estado_cultural=estado_str,
            operaciones_activas=ops_str,
            especulaciones=esp_str,
            estudios=est_str,
            historial_reciente=historial or "Sin historial disponible.",
            proyeccion=proyeccion or "Sin proyección disponible.",
            fecha=estado.fecha.strftime("%Y-%m-%d"),
        )

        try:
            resultado = self.ejecutar_prompt(prompt, formato_json=True)
        except Exception as e:
            logger.error(f"Error en Redactor: {e}")
            return self._fallback(estado, operaciones)

        return self._parsear_resultado(resultado, estado, operaciones)

    def _formatear_estado(self, estado: EstadoCultural) -> str:
        lineas = [f"Sociedad: {estado.sociedad}"]
        lineas.append(f"M = ({estado.M_m:.1f}, {estado.M_l:.1f}, {estado.M_s:.1f})")
        lineas.append(f"δ = {estado.delta_promedio:.1f}°")
        lineas.append(f"Coherente: {estado.coherente}")
        if estado.nodos_fragiles:
            lineas.append(f"Nodos frágiles: {', '.join(estado.nodos_fragiles)}")
        lineas.append("")
        for n in estado.nodos:
            frag = "⚠" if n.fragil else " "
            lineas.append(f"  [{frag}] {n.nodo_id}: M_m={n.dimension_m:.1f} M_l={n.dimension_l:.1f} M_s={n.dimension_s:.1f} δ={n.delta:.1f}°")
        return "\n".join(lineas)

    def _formatear_operaciones(self, ops: list[OperacionCinetica]) -> str:
        if not ops:
            return "Ninguna operación activa detectada."
        lineas = []
        for o in ops:
            lineas.append(f"- {o.codigo} ({o.nombre}): intensidad {o.intensidad:.2f}")
            lineas.append(f"  Nodos: {', '.join(o.nodos_implicados)}")
            lineas.append(f"  {o.descripcion}")
        return "\n".join(lineas)

    def _formatear_especulaciones(self, esp: list[Especulacion]) -> str:
        if not esp:
            return "El Artista no generó especulaciones hoy."
        lineas = []
        for e in esp:
            lineas.append(f"- {e.id}: {e.patron_id} (confianza: {e.confianza:.2f})")
            lineas.append(f"  {e.argumento}")
            if e.nodos_sugeridos:
                lineas.append(f"  Nodos sugeridos: {', '.join(e.nodos_sugeridos)}")
        return "\n".join(lineas)

    def _formatear_estudios(self, estudios: list[Estudio]) -> str:
        if not estudios:
            return "No se realizaron estudios hoy."
        lineas = []
        for e in estudios:
            lineas.append(f"- {e.id}: patrón {e.patron_id} → {e.estado.value}")
            for dim, analisis in e.analisis.items():
                status = "✓" if analisis.confirmado else "✗"
                lineas.append(f"  {dim}: {status} (confianza: {analisis.confianza:.2f})")
                lineas.append(f"    {analisis.conclusion}")
        return "\n".join(lineas)

    def _parsear_resultado(self, resultado: dict, estado: EstadoCultural, operaciones: list[OperacionCinetica]) -> InformeDiario:
        alertas_data = resultado.get("alertas", [])
        alertas = []
        for a in alertas_data:
            try:
                tipo = TipoAlerta(a.get("tipo", "riesgo_estructural"))
            except ValueError:
                tipo = TipoAlerta.riesgo_estructural
            alertas.append(Alerta(tipo=tipo, mensaje=a.get("mensaje", "")))

        dash_data = resultado.get("dashboard", {})

        return InformeDiario(
            panorama=resultado.get("panorama", ""),
            dinamicas=resultado.get("dinamicas", ""),
            especulaciones_y_estudios=resultado.get("especulaciones_y_estudios", ""),
            alertas=alertas,
            mirada_adelante=resultado.get("mirada_adelante", ""),
            resumen_ejecutivo=resultado.get("resumen_ejecutivo", ""),
            dashboard=DashboardData(
                metrica_principal=dash_data.get("metrica_principal", f"δ = {estado.delta_promedio:.1f}°"),
                cambio_clave=dash_data.get("cambio_clave", ""),
                nodos_criticos=dash_data.get("nodos_criticos", estado.nodos_fragiles),
                patrones_nuevos=dash_data.get("patrones_nuevos", []),
            ),
        )

    def _fallback(self, estado: EstadoCultural, operaciones: list[OperacionCinetica]) -> InformeDiario:
        alertas = []
        if estado.delta_promedio >= 45:
            alertas.append(Alerta(
                tipo=TipoAlerta.reconfiguracion,
                mensaje=f"δ = {estado.delta_promedio:.1f}°: umbral de reconfiguración alcanzado",
            ))
        return InformeDiario(
            panorama=f"Estado cultural: M=({estado.M_m:.1f}, {estado.M_l:.1f}, {estado.M_s:.1f}), δ={estado.delta_promedio:.1f}°",
            dinamicas=f"{len(operaciones)} operaciones detectadas.",
            resumen_ejecutivo=f"δ = {estado.delta_promedio:.1f}° | Coherente: {estado.coherente}",
            alertas=alertas,
        )
