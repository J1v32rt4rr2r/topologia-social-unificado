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
from topologia.prompts import PromptLoader


class Redactor(Agent):
    def __init__(self):
        super().__init__(ConfigAgente(
            nombre="Redactor",
            prompt="",
            temperatura=0.5,
            modelo="deepseek-chat",
            max_tokens=2048,
        ))
        self.prompts = PromptLoader()

    def sintetizar(
        self,
        estado: EstadoCultural,
        operaciones: list[OperacionCinetica],
        especulaciones: list[Especulacion],
        estudios: list[Estudio],
        historial: str = "",
        proyeccion: str = "",
        analisis_formas: str = "",
        graficos_generados: list[str] | None = None,
    ) -> InformeDiario:
        estado_str = self._formatear_estado(estado)
        ops_str = self._formatear_operaciones(operaciones)
        esp_str = self._formatear_especulaciones(especulaciones)
        est_str = self._formatear_estudios(estudios)
        formas_str = analisis_formas or "Sin análisis de formas complejas disponible."
        graf_str = self._formatear_graficos(graficos_generados)
        tens_str = self._formatear_tensiones_latentes(estudios)

        prompt = self.prompts.load("redactor_sintesis",
            estado_cultural=estado_str,
            operaciones_activas=ops_str,
            especulaciones=esp_str,
            estudios=est_str,
            tensiones_latentes=tens_str,
            historial_reciente=historial or "Sin historial disponible.",
            proyeccion=proyeccion or "Sin proyección disponible.",
            analisis_formas=formas_str,
            graficos_generados=graf_str,
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
        lineas.append("Dimensiones culturales:")
        lineas.append(f"  M_m (Matriz Material): {estado.M_m:.1f}")
        lineas.append(f"  M_l (Matriz Lógico-Valórica): {estado.M_l:.1f}")
        lineas.append(f"  M_s (Matriz Social): {estado.M_s:.1f}")
        lineas.append(f"δ = {estado.delta_promedio:.1f}°")
        lineas.append(f"Coherente: {estado.coherente}")
        if estado.nodos_fragiles:
            lineas.append(f"Nodos frágiles: {', '.join(estado.nodos_fragiles)}")
        lineas.append("")
        for n in estado.nodos:
            frag = "⚠" if n.fragil else " "
            m, l, s = n.dimension_m, n.dimension_l, n.dimension_s
            if abs(l - s) <= 0.5:
                pat = "EIC"  # estructura ideológica consolidada
            elif l > m and s > m:
                pat = "ANH"  # anhelo insatisfecho
            elif m > l and m > s:
                pat = "MAT"  # materialidad dominante
            else:
                pat = ""
            lineas.append(f"  [{frag}] {n.nodo_id}: M_m={m:.1f} M_l={l:.1f} M_s={s:.1f} δ={n.delta:.1f}° [{pat}]")
        if estado.m_m:
            lineas.append(f"\nFormas complejas (e^(2πi / m)):")
            lineas.append(f"  M_m (Matriz Material): m={estado.m_m:.3f} θ={estado.theta_m:.1f}°")
            lineas.append(f"  M_l (Matriz Lógico-Valórica): m={estado.m_l:.3f} θ={estado.theta_l:.1f}°")
            lineas.append(f"  M_s (Matriz Social): m={estado.m_s:.3f} θ={estado.theta_s:.1f}°")
            lineas.append(f"  Coherencia interna: {estado.coherencia_interna:.1f}°")
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

    def _formatear_tensiones_latentes(self, estudios: list[Estudio]) -> str:
        tensiones = [e for e in estudios if e.tension_latente]
        if not tensiones:
            return "No se identificaron tensiones latentes."
        lineas = []
        for e in tensiones:
            lineas.append(f"- Pregunta: {e.pregunta_investigada}")
            lineas.append(f"  Hallazgo: {e.respuesta[:200]}")
        return "\n".join(lineas)

    def _formatear_estudios(self, estudios: list[Estudio]) -> str:
        if not estudios:
            return "No se realizaron estudios hoy."
        lineas = []
        for e in estudios:
            tag = "🔮 TENSIÓN LATENTE" if e.tension_latente else "investigado"
            lineas.append(f"- {e.id}: patrón {e.patron_id} → {tag}")
            if e.pregunta_investigada:
                lineas.append(f"  Pregunta: {e.pregunta_investigada}")
            lineas.append(f"  Respuesta: {e.respuesta[:200]}")
            for dim, analisis in e.analisis.items():
                lineas.append(f"  {dim}: hallazgo={analisis.hallazgo[:100]} (confianza: {analisis.confianza:.2f})")
        return "\n".join(lineas)

    def _formatear_graficos(self, graficos: list[str] | None = None) -> str:
        GRAFICOS = {
            "grafico_plano_complejo.png": "Vectores M_m, M_l, M_s en círculo unitario (coherencia estructural vs tensión transformadora)",
            "grafico_rotacion_angular.png": "Δθ entre estado actual y anterior por dimensión",
            "grafico_triangulo_coherencia.png": "Triángulo de coherencia entre las 3 formas complejas",
            "grafico_radar_nodos.png": "Puntuaciones normalizadas de los 9 nodos por dimensión",
            "grafico_mapa_calor_nodos.png": "Matriz 9×9: variación nodal por transversal (M_m, M_s, M_l) con antes/después/Δ",
        }
        if graficos:
            lineas = [f"- {g}: {GRAFICOS.get(g, '')}" for g in graficos if g in GRAFICOS]
        else:
            lineas = [f"- {name}: {desc}" for name, desc in GRAFICOS.items()]
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
