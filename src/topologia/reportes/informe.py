from __future__ import annotations

from datetime import datetime
from pathlib import Path

from topologia.math.operations import detectar_operaciones
from topologia.models.schemas import (
    EstadoCultural,
    Estudio,
    Especulacion,
    InformeDiario,
    ItemInformativo,
    OperacionCinetica,
)
from topologia.storage.store import FileStore


def generar_informe(
    sociedad: str = "Chile",
    estado: EstadoCultural | None = None,
    operaciones: list[OperacionCinetica] | None = None,
    especulaciones: list[Especulacion] | None = None,
    estudios: list[Estudio] | None = None,
    items_por_nodo: dict[str, list[ItemInformativo]] | None = None,
    informe_redactor: InformeDiario | None = None,
) -> str:
    store = FileStore()
    if estado is None:
        estado = store.cargar_estado(sociedad)
    if estado is None:
        return f"No hay datos para {sociedad}"

    if operaciones is None:
        operaciones = detectar_operaciones(estado)

    fecha = estado.fecha.strftime("%Y-%m-%d %H:%M")
    lineas: list[str] = []

    # --- Encabezado ---
    lineas.append(f"# Informe Topologico: {sociedad}")
    lineas.append(f"**Fecha:** {fecha}")
    lineas.append("")

    # --- Resumen ejecutivo ---
    if informe_redactor:
        lineas.append("## Resumen Ejecutivo")
        lineas.append(informe_redactor.resumen_ejecutivo)
        lineas.append("")

    # --- Alertas ---
    if informe_redactor and informe_redactor.alertas:
        lineas.append("## Alertas")
        for a in informe_redactor.alertas:
            icono = "CRITICAL" if a.tipo.value == "reconfiguracion" else "WARNING"
            lineas.append(f"- **[ {icono} ]** {a.mensaje}")
        lineas.append("")

    # --- Estado Global ---
    lineas.append("## Estado Global")
    lineas.append(f"| Metrica | Valor |")
    lineas.append(f"|---------|-------|")
    lineas.append(f"| M_m (Material) | {estado.M_m:.1f} |")
    lineas.append(f"| M_l (Logico-valorativa) | {estado.M_l:.1f} |")
    lineas.append(f"| M_s (Social) | {estado.M_s:.1f} |")
    lineas.append(f"| Brecha angular (delta) | {estado.delta_promedio:.1f}° |")
    lineas.append(f"| Coherencia | {'Si' if estado.coherente else 'NO'} |")
    if estado.nodos_fragiles:
        lineas.append(f"| Nodos fragiles | {', '.join(estado.nodos_fragiles)} |")
    lineas.append("")

    # --- Detalle por Nodo ---
    lineas.append("## Detalle por Nodo")
    lineas.append("")

    for n in estado.nodos:
        frag = " FRAGIL" if n.fragil else ""
        lineas.append(f"### {n.nodo_id}{frag}")
        lineas.append(f"| Dimension | Valor | Tendencia | δ |")
        lineas.append(f"|-----------|-------|-----------|-----|")
        lineas.append(f"| Material (M_m) | {n.dimension_m:.1f} | {n.tendencia_m.value} | {n.delta:.1f}° |")
        lineas.append(f"| Logico-valorativa (M_l) | {n.dimension_l:.1f} | {n.tendencia_l.value} | |")
        lineas.append(f"| Social (M_s) | {n.dimension_s:.1f} | {n.tendencia_s.value} | |")
        lineas.append("")

        if n.justificacion_m:
            lineas.append(f"**Justificacion M_m:** {n.justificacion_m}")
        if n.justificacion_l:
            lineas.append(f"**Justificacion M_l:** {n.justificacion_l}")
        if n.justificacion_s:
            lineas.append(f"**Justificacion M_s:** {n.justificacion_s}")

        # Fuentes del nodo
        if items_por_nodo and n.nodo_id in items_por_nodo:
            items = items_por_nodo[n.nodo_id]
            if items:
                lineas.append("")
                lineas.append("**Fuentes consultadas:**")
                for it in items[:5]:
                    if it.url:
                        lineas.append(f"- [{it.titulo}]({it.url})")
                    else:
                        lineas.append(f"- {it.titulo} ({it.fuente})")
        lineas.append("")

    # --- Operaciones Cineticas ---
    if operaciones:
        lineas.append("## Operaciones Cineticas Detectadas")
        lineas.append("")
        for o in operaciones:
            intensidad_pct = o.intensidad * 100
            barra = "█" * int(intensidad_pct / 10) + "░" * (10 - int(intensidad_pct / 10))
            lineas.append(f"**{o.codigo}**: {o.nombre}  `{barra} {intensidad_pct:.0f}%`")
            lineas.append(f"- Nodos: {', '.join(o.nodos_implicados)}")
            lineas.append(f"- {o.descripcion}")
            if o.evidencia:
                lineas.append(f"- Evidencia: {o.evidencia}")
            lineas.append("")

    # --- Especulaciones del Artista ---
    if especulaciones:
        lineas.append("## Especulaciones del Artista")
        lineas.append("")
        for e in especulaciones:
            lineas.append(f"### {e.id}: {e.patron_id}")
            lineas.append(f"- Confianza: {e.confianza:.0%}")
            lineas.append(f"- Argumento: {e.argumento}")
            if e.nodos_sugeridos:
                lineas.append(f"- Nodos sugeridos: {', '.join(e.nodos_sugeridos)}")
            if e.pregunta_abierta:
                lineas.append(f"- Pregunta abierta: {e.pregunta_abierta}")
            lineas.append("")

    # --- Estudios ---
    if estudios:
        lineas.append("## Resultados de Estudios")
        lineas.append("")
        for est in estudios:
            linea_est = f"### {est.id}: patron {est.patron_id}"
            if est.veredicto == "validado":
                linea_est += " [VALIDADO]"
            elif est.veredicto == "refutado":
                linea_est += " [REFUTADO]"
            elif est.veredicto == "parcial":
                linea_est += " [PARCIAL]"
            lineas.append(linea_est)
            for dim_key, dim_analisis in est.analisis.items():
                status = "CONFIRMADO" if dim_analisis.confirmado else "NO CONFIRMADO"
                lineas.append(f"- **{dim_key}**: {status} (confianza: {dim_analisis.confianza:.0%})")
                if dim_analisis.evidencia:
                    lineas.append(f"  - Evidencia: {dim_analisis.evidencia}")
                if dim_analisis.contraevidencia:
                    lineas.append(f"  - Contraevidencia: {dim_analisis.contraevidencia}")
                lineas.append(f"  - Conclusion: {dim_analisis.conclusion}")
            lineas.append("")

    # --- Mirada hacia adelante ---
    if informe_redactor and informe_redactor.mirada_adelante:
        lineas.append("## Mirada hacia Adelante")
        lineas.append(informe_redactor.mirada_adelante)
        lineas.append("")

    # --- Historial reciente ---
    fechas = store.listar_estados(sociedad)
    if len(fechas) > 1:
        lineas.append("## Historial Reciente")
        lineas.append("")
        lineas.append("| Fecha | δ | M_m | M_l | M_s |")
        lineas.append("|-------|-----|-----|-----|-----|")
        for f in fechas[-7:]:
            e = store.cargar_estado(sociedad, f)
            if e:
                lineas.append(f"| {f} | {e.delta_promedio:.1f}° | {e.M_m:.1f} | {e.M_l:.1f} | {e.M_s:.1f} |")
        lineas.append("")

    # --- Guardar ---
    ruta = Path.home() / ".local" / "share" / "topologia-social" / "data" / "reportes"
    ruta.mkdir(parents=True, exist_ok=True)
    archivo = ruta / f"informe_{sociedad}_{datetime.now().strftime('%Y-%m-%d')}.md"
    contenido = "\n".join(lineas)
    archivo.write_text(contenido, encoding="utf-8")

    return str(archivo)
