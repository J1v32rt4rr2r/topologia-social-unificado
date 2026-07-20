from __future__ import annotations

from datetime import datetime
from html import escape

from topologia.math.operations import detectar_operaciones
from topologia.models.schemas import (
    EstadoCultural,
    Estudio,
    Especulacion,
    InformeDiario,
    ItemInformativo,
    OperacionCinetica,
)
from topologia.paths import get_reportes_dir
from topologia.storage.store import FileStore
from topologia.web.brechas import detectar_brechas, resumen_brechas, NODOS_CULTURALES

FUENTES_INTERNACIONALES = {"news.google.com", "www.bbc.com", "google.com", "bbc.com"}

CSS = """
:root {
  --bg: #f5f6fa;
  --card-bg: #ffffff;
  --text: #1a1a2e;
  --text-secondary: #555;
  --accent: #e94560;
  --accent2: #0f3460;
  --green: #2ecc71;
  --yellow: #f39c12;
  --red: #e74c3c;
  --blue: #3498db;
  --border: #e0e0e0;
  --shadow: 0 2px 12px rgba(0,0,0,0.08);
  --radius: 12px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Georgia', 'Times New Roman', serif;
  font-size: 17px;
  line-height: 1.7;
  color: var(--text);
  background: var(--bg);
}
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }

/* HEADER */
.header {
  text-align: center;
  padding: 40px 20px 30px;
  border-bottom: 3px double var(--accent2);
  margin-bottom: 28px;
}
.header h1 {
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 42px;
  font-weight: 800;
  color: var(--accent2);
  letter-spacing: 4px;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.header .subtitle {
  font-size: 18px;
  color: var(--text-secondary);
  font-style: italic;
}
.header .fecha {
  font-size: 16px;
  color: var(--text-secondary);
  margin-top: 8px;
}

/* PORTADA BOX */
.portada-box {
  background: linear-gradient(135deg, var(--accent2), #16213e);
  color: white;
  border-radius: var(--radius);
  padding: 32px 40px;
  margin-bottom: 28px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 24px;
  align-items: center;
}
.portada-metrica-principal {
  text-align: center;
}
.portada-metrica-principal .valor {
  font-size: 56px;
  font-weight: 800;
  line-height: 1;
}
.portada-metrica-principal .label {
  font-size: 14px;
  opacity: 0.7;
  margin-top: 4px;
}
.portada-metrica-secundaria {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.portada-metrica-secundaria .item {
  background: rgba(255,255,255,0.1);
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 15px;
}
.portada-metrica-secundaria .item strong {
  font-size: 20px;
}
.portada-resumen {
  font-size: 18px;
  font-style: italic;
  line-height: 1.6;
  max-width: 400px;
  border-left: 3px solid rgba(255,255,255,0.3);
  padding-left: 20px;
}

/* THREE COLUMNS */
.tres-columnas {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 20px;
  margin-bottom: 28px;
}
@media (max-width: 900px) {
  .tres-columnas { grid-template-columns: 1fr; }
}
.columna {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: var(--shadow);
}
.columna h3 {
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: var(--accent2);
  border-bottom: 2px solid var(--accent);
  padding-bottom: 8px;
  margin-bottom: 16px;
}
.columna p {
  font-size: 16px;
  line-height: 1.7;
  margin-bottom: 10px;
  color: var(--text);
}
.tabla-nodos {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.tabla-nodos th {
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
}
.tabla-nodos td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
}
.tabla-nodos .fragil { color: var(--red); font-weight: 700; }
.tabla-nodos .delta-alto { color: var(--red); font-weight: 600; }

/* FORMAS COMPLEJAS */
.formas-box {
  background: var(--card-bg);
  border: 2px solid var(--accent2);
  border-radius: var(--radius);
  padding: 28px;
  margin-bottom: 28px;
}
.formas-box h3 {
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: var(--accent2);
  margin-bottom: 16px;
}
.formas-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
@media (max-width: 600px) {
  .formas-grid { grid-template-columns: 1fr; }
}
.formas-vectores, .formas-deltas {
  font-size: 15px;
  line-height: 2;
}
.formas-vectores .dim { display: inline-block; width: 80px; font-weight: 700; }
.formas-vectores .m { color: #00d4ff; }
.formas-vectores .l { color: #c084fc; }
.formas-vectores .s { color: #ff6b35; }
.formas-coherencia {
  grid-column: 1 / -1;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

/* TWO COLUMNS */
.dos-columnas {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 28px;
}
@media (max-width: 900px) {
  .dos-columnas { grid-template-columns: 1fr; }
}

/* NOTICIAS DESTACADAS */
.noticia-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 15px;
}
.noticia-item:last-child { border-bottom: none; }
.noticia-titulo { font-weight: 600; }
.noticia-fuente {
  font-size: 13px;
  color: var(--text-secondary);
  display: block;
}

/* ESPECULACIONES / ESTUDIOS CARDS */
.card {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 14px;
  box-shadow: var(--shadow);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.card-header h4 { font-size: 16px; color: var(--accent2); }
.confianza-pct {
  background: var(--accent);
  color: white;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}
.card-texto { font-size: 15px; line-height: 1.6; margin-bottom: 8px; }
.card-meta { font-size: 13px; color: var(--text-secondary); }
.veredicto {
  font-size: 13px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 12px;
}
.veredicto.refutado { background: #fde8e8; color: var(--red); }
.veredicto.parcial { background: #fef3cd; color: var(--yellow); }
.veredicto.validado { background: #e8fde8; color: var(--green); }
.analisis-dim {
  font-size: 14px;
  margin: 4px 0;
  padding: 4px 8px;
  background: var(--bg);
  border-radius: 6px;
}
.analisis-dim .ok { color: var(--green); font-weight: 600; }
.analisis-dim .fail { color: var(--red); font-weight: 600; }

/* GRÁFICOS */
.graficos-seccion {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 28px;
  margin-bottom: 28px;
  box-shadow: var(--shadow);
}
.graficos-seccion h3 {
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: var(--accent2);
  margin-bottom: 16px;
}
.graficos-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
@media (max-width: 900px) {
  .graficos-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 600px) {
  .graficos-grid { grid-template-columns: 1fr 1fr; }
}
.grafico-thumb {
  text-align: center;
}
.grafico-thumb img {
  width: 100%;
  border-radius: 8px;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: transform 0.2s;
}
.grafico-thumb img:hover { transform: scale(1.05); }
.grafico-thumb .nombre {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

/* HISTORIAL */
.historial-box {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 28px;
  margin-bottom: 28px;
  box-shadow: var(--shadow);
}
.historial-box h3 {
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: var(--accent2);
  margin-bottom: 16px;
}
.tabla-historial {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.tabla-historial th {
  background: var(--bg);
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid var(--border);
}
.tabla-historial td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
}
.subida { color: var(--red); font-weight: 600; }
.bajada { color: var(--green); font-weight: 600; }
.estable { color: var(--text-secondary); }

/* ALERTAS */
.alertas-box {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 28px;
  margin-bottom: 28px;
  box-shadow: var(--shadow);
}
.alertas-box h3 {
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: var(--accent2);
  margin-bottom: 16px;
}
.alerta-card {
  padding: 14px 18px;
  border-radius: 8px;
  margin-bottom: 10px;
  font-size: 16px;
}
.alerta-card.critica { background: #fde8e8; border-left: 4px solid var(--red); }
.alerta-card.advertencia { background: #fef3cd; border-left: 4px solid var(--yellow); }

/* MIRADA ADELANTE */
.mirada-box {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 28px;
  margin-bottom: 28px;
  box-shadow: var(--shadow);
}
.mirada-box h3 {
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: var(--accent2);
  margin-bottom: 16px;
}

/* OPERACIONES */
.operacion-item {
  padding: 6px 0;
  font-size: 15px;
  border-bottom: 1px solid var(--border);
}
.operacion-item:last-child { border-bottom: none; }
.operacion-codigo {
  display: inline-block;
  background: var(--accent2);
  color: white;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  margin-right: 6px;
}

/* FOOTER */
.footer {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
  font-size: 13px;
  border-top: 1px solid var(--border);
}
"""


def _filtrar_fuentes(items: list[ItemInformativo]) -> list[ItemInformativo]:
    tiene_local = any(
        not any(ext in (it.fuente or it.url or "") for ext in FUENTES_INTERNACIONALES)
        for it in items
    )
    if tiene_local:
        return [
            it for it in items
            if not any(ext in (it.fuente or it.url or "") for ext in FUENTES_INTERNACIONALES)
        ]
    return items


def _build_cabecera(sociedad: str, fecha: str) -> str:
    return f"""<div class="header">
    <h1>Topolog&iacute;a Social</h1>
    <div class="subtitle">Informe de Observaci&oacute;n Cultural &mdash; {escape(sociedad)}</div>
    <div class="fecha">{escape(fecha)}</div>
  </div>"""


def _build_portada(estado: EstadoCultural, informe_redactor: InformeDiario | None) -> str:
    coh = "Coherente" if estado.coherente else "Incoherente"
    resumen = ""
    if informe_redactor and informe_redactor.resumen_ejecutivo:
        resumen = f'<div class="portada-resumen">{escape(informe_redactor.resumen_ejecutivo)}</div>'

    frag_list = estado.nodos_fragiles or []
    frag_html = "".join(
        f'<span class="item">⚠ <strong>{escape(n)}</strong></span>'
        for n in frag_list
    ) if frag_list else ""

    return f"""<div class="portada-box">
    <div class="portada-metrica-principal">
      <div class="valor" style="color:{"#2ecc71" if estado.coherente else "#e94560"}">{estado.delta_promedio:.0f}°</div>
      <div class="label">{coh}</div>
    </div>
    <div class="portada-metrica-secundaria">
      <span class="item">M_m: <strong>{estado.M_m:.1f}</strong></span>
      <span class="item">M_l: <strong>{estado.M_l:.1f}</strong></span>
      <span class="item">M_s: <strong>{estado.M_s:.1f}</strong></span>
      <span class="item">Era: <strong>{estado.era_k}</strong></span>
      {frag_html}
    </div>
    {resumen}
  </div>"""


def _build_tres_columnas(estado: EstadoCultural, informe_redactor: InformeDiario | None,
                          items_por_nodo: dict[str, list[ItemInformativo]] | None) -> str:
    panorama = ""
    if informe_redactor and informe_redactor.panorama:
        panorama = f'<p>{escape(informe_redactor.panorama)}</p>'

    noticias_html = ""
    if items_por_nodo:
        items = []
        for nid, nitems in items_por_nodo.items():
            for it in nitems[:2]:
                items.append((nid, it))
        items = items[:9]
        for nid, it in items:
            noticias_html += f"""<div class="noticia-item">
        <span class="noticia-titulo">{escape(it.titulo)}</span>
        <span class="noticia-fuente">{escape(nid)} &mdash; {escape(it.fuente)}</span>
      </div>"""
    if not noticias_html:
        noticias_html = '<p style="color:var(--text-secondary);">Sin noticias destacadas.</p>'

    nodos = sorted(estado.nodos, key=lambda n: (not n.fragil, -n.delta))
    filas = ""
    for n in nodos:
        frag = "⚠" if n.fragil else ""
        cls_frag = ' class="fragil"' if n.fragil else ""
        cls_delta = ' class="delta-alto"' if n.delta > 45 else ""
        filas += f"""<tr{cls_frag}>
      <td>{escape(n.nodo_id)} {frag}</td>
      <td>{n.dimension_m:.1f}</td>
      <td>{n.dimension_l:.1f}</td>
      <td>{n.dimension_s:.1f}</td>
      <td{cls_delta}>{n.delta:.1f}°</td>
    </tr>"""

    return f"""<div class="tres-columnas">
    <div class="columna">
      <h3>Panorama General</h3>
      {panorama}
    </div>
    <div class="columna">
      <h3>Noticias Destacadas</h3>
      {noticias_html}
    </div>
    <div class="columna">
      <h3>Estado Cultural</h3>
      <table class="tabla-nodos">
        <tr><th>Nodo</th><th>M_m</th><th>M_l</th><th>M_s</th><th>δ</th></tr>
        {filas}
      </table>
    </div>
  </div>"""


def _build_formas_complejas(estado: EstadoCultural) -> str:
    if not estado.m_m:
        return ""
    vectores = [
        ("M_m", estado.m_m, estado.theta_m, "m"),
        ("M_l", estado.m_l, estado.theta_l, "l"),
        ("M_s", estado.m_s, estado.theta_s, "s"),
    ]
    v_html = "".join(
        f'<div><span class="dim {cls}">{nom}</span> m={m:.3f} &theta;={th:.1f}°</div>'
        for nom, m, th, cls in vectores
    )

    store = FileStore()
    fechas = store.listar_estados(estado.sociedad)
    d_html = ""
    if len(fechas) >= 2:
        anterior = store.cargar_estado(estado.sociedad, fechas[-2])
        if anterior and anterior.m_m:
            pares = [
                ("M_m", anterior.theta_m, estado.theta_m),
                ("M_l", anterior.theta_l, estado.theta_l),
                ("M_s", anterior.theta_s, estado.theta_s),
            ]
            d_html = "".join(
                f'<div><strong>{nom}</strong> &Delta;&theta;={abs(t1 - t0):.1f}° '
                f'({"↻" if t1 >= t0 else "↺"})</div>'
                for nom, t0, t1 in pares
            )
        else:
            d_html = "<div>Sin referencia anterior.</div>"
    else:
        d_html = "<div>Sin referencia anterior.</div>"

    coh = f"Coherencia interna: {estado.coherencia_interna:.1f}°"
    if estado.coherencia_interna < 15:
        coh += " &mdash; Alta cohesi&oacute;n entre dimensiones"
    elif estado.coherencia_interna > 45:
        coh += " &mdash; Divergencia significativa"

    return f"""<div class="formas-box">
    <h3>An&aacute;lisis de Formas Complejas (e^(2&pi;i / m))</h3>
    <div class="formas-grid">
      <div class="formas-vectores">
        <strong>Vectores culturales:</strong>
        {v_html}
      </div>
      <div class="formas-deltas">
        <strong>Rotaci&oacute;n respecto a ayer:</strong>
        {d_html}
      </div>
      <div class="formas-coherencia">{coh}</div>
    </div>
  </div>"""


def _build_dos_columnas(especulaciones: list[Especulacion] | None,
                         estudios: list[Estudio] | None,
                         operaciones: list[OperacionCinetica] | None) -> str:
    esp_html = ""
    if especulaciones:
        for e in especulaciones:
            conf_pct = int(e.confianza * 100)
            nodos_str = ", ".join(e.nodos_sugeridos) if e.nodos_sugeridos else ""
            pregunta = f'<div class="card-meta">💬 {escape(e.pregunta_abierta)}</div>' if e.pregunta_abierta else ""
            esp_html += f"""<div class="card">
        <div class="card-header">
          <h4>{escape(e.id)}: {escape(e.patron_id)}</h4>
          <span class="confianza-pct">{conf_pct}%</span>
        </div>
        <div class="card-texto">{escape(e.argumento)}</div>
        <div class="card-meta">🎯 {escape(nodos_str)}</div>
        {pregunta}
      </div>"""
    if not esp_html:
        esp_html = '<p style="color:var(--text-secondary);">Sin especulaciones.</p>'

    est_html = ""
    if estudios:
        for est in estudios:
            v_lbl = est.veredicto.upper() if est.veredicto else "PENDIENTE"
            dims_html = ""
            for dk, dim in est.analisis.items():
                status = "✓ Confirmado" if dim.confirmado else "✗ No confirmado"
                cls = "ok" if dim.confirmado else "fail"
                poss = f" posible:{dim.posibilidad}" if dim.posibilidad else ""
                real = f" real:{dim.realidad}" if dim.realidad else ""
                dims_html += f"""<div class="analisis-dim">
          <strong>{escape(dk)}</strong>: <span class="{cls}">{status}</span>
          (confianza: {dim.confianza:.0%}{poss}{real})
          <br><span style="font-size:13px;">{escape(dim.conclusion)}</span>
        </div>"""
            est_html += f"""<div class="card">
        <div class="card-header">
          <h4>{escape(est.id)}: {escape(est.patron_id)}</h4>
          <span class="veredicto {est.veredicto or 'pendiente'}">{v_lbl}</span>
        </div>
        {dims_html}
      </div>"""
    if not est_html:
        est_html = '<p style="color:var(--text-secondary);">Sin estudios.</p>'

    ops_html = ""
    if operaciones:
        ops_html = "<h4 style='margin-bottom:10px;'>Operaciones Activas</h4>"
        for o in operaciones:
            pct = int(o.intensidad * 100)
            barra = "█" * (pct // 10) + "░" * (10 - pct // 10)
            ops_html += f"""<div class="operacion-item">
        <span class="operacion-codigo">{escape(o.codigo)}</span>
        <strong>{escape(o.nombre)}</strong> {barra} {pct}%
        <br><span style="font-size:14px;">{escape(o.descripcion)}</span>
      </div>"""

    return f"""<div class="dos-columnas">
    <div class="columna">
      <h3>Especulaciones</h3>
      {esp_html}
    </div>
    <div class="columna">
      <h3>Estudios</h3>
      {est_html}
      {ops_html}
    </div>
  </div>"""


import base64

def _build_graficos() -> str:
    from topologia.paths import get_reportes_dir
    reportes_dir = get_reportes_dir()
    nombres = [
        ("grafico_plano_complejo.png", "Plano Complejo"),
        ("grafico_rotacion_angular.png", "Rotaci&oacute;n Angular"),
        ("grafico_triangulo_coherencia.png", "Tri&aacute;ngulo Coherencia"),
        ("grafico_radar_nodos.png", "Radar Nodos"),
        ("grafico_mapa_calor_nodos.png", "Mapa de Calor"),
    ]
    thumbs = ""
    for name, label in nombres:
        ruta = reportes_dir / name
        if ruta.exists():
            b64 = base64.b64encode(ruta.read_bytes()).decode()
            src = f"data:image/png;base64,{b64}"
        else:
            src = ""
        thumbs += f"""<div class="grafico-thumb">
      <a href="{src if not src else name}" target="_blank">
        <img src="{src}" alt="{label}" loading="lazy" style="{"opacity:0.4;" if not src else ""}">
      </a>
      <div class="nombre">{label}{" (no disponible)" if not src else ""}</div>
    </div>"""
    return f"""<div class="graficos-seccion">
    <h3>Gr&aacute;ficos del D&iacute;a</h3>
    <div class="graficos-grid">
      {thumbs}
    </div>
  </div>"""


def _build_historial(sociedad: str) -> str:
    store = FileStore()
    fechas = store.listar_estados(sociedad)
    if len(fechas) < 2:
        return ""
    estados = []
    for f in fechas[-7:]:
        e = store.cargar_estado(sociedad, f)
        if e:
            estados.append((f, e))
    filas = ""
    for i, (f, e) in enumerate(estados):
        diff_html = ""
        if i > 0:
            diff = e.delta_promedio - estados[i - 1][1].delta_promedio
            if diff > 1:
                diff_html = f'<span class="subida">⬆ +{diff:.1f}°</span>'
            elif diff < -1:
                diff_html = f'<span class="bajada">⬇ {diff:.1f}°</span>'
            else:
                diff_html = f'<span class="estable">→ {diff:.1f}°</span>'
        filas += f"<tr><td>{f}</td><td>{e.delta_promedio:.1f}°</td><td>{e.M_m:.1f}</td><td>{e.M_l:.1f}</td><td>{e.M_s:.1f}</td><td>{diff_html}</td></tr>\n"
    return f"""<div class="historial-box">
    <h3>Historial Reciente</h3>
    <table class="tabla-historial">
      <tr><th>Fecha</th><th>&delta;</th><th>M_m</th><th>M_l</th><th>M_s</th><th>&Delta;</th></tr>
      {filas}
    </table>
  </div>"""


def _build_alertas(informe_redactor: InformeDiario | None) -> str:
    if not informe_redactor or not informe_redactor.alertas:
        return ""
    items = ""
    for a in informe_redactor.alertas:
        tipo_cls = "critica" if a.tipo.value == "reconfiguracion" else "advertencia"
        items += f'<div class="alerta-card {tipo_cls}">{escape(a.mensaje)}</div>'
    return f"""<div class="alertas-box">
    <h3>Alertas</h3>
    {items}
  </div>"""


def _build_mirada(informe_redactor: InformeDiario | None) -> str:
    if not informe_redactor or not informe_redactor.mirada_adelante:
        return ""
    return f"""<div class="mirada-box">
    <h3>Mirada hacia Adelante</h3>
    <p style="font-size:16px;line-height:1.7;">{escape(informe_redactor.mirada_adelante)}</p>
  </div>"""


def _build_cobertura(brechas: dict[str, dict]) -> str:
    if not brechas:
        return ""

    planos = [nid for nid, info in brechas.items()
              if nid in NODOS_CULTURALES and info.get("score_plano")]
    alerta_ban = ""
    if planos:
        planos_str = ", ".join(planos)
        alerta_ban = f"""<div style="background:#fff3cd;border:1px solid #856404;border-radius:8px;padding:12px 16px;margin-bottom:16px;color:#856404;">
      <strong>&#9888; Sin cobertura:</strong> los nodos {escape(planos_str)} no recibieron datos en este ciclo.
      Sus dimensiones aparecen planas (5.0/5.0/5.0) porque no se encontraron art&iacute;culos relevantes.
      Considere expandir fuentes o t&eacute;rminos de b&uacute;squeda para estos nodos.
    </div>"""

    hay_items = not brechas.get("_meta", {}).get("modo") == "standalone"
    if not hay_items:
        con_datos = sum(1 for nid in NODOS_CULTURALES if not brechas.get(nid, {}).get("score_plano", True))
        sin_datos = 9 - con_datos
        filas = ""
        for nid in NODOS_CULTURALES:
            info = brechas.get(nid, {})
            score_plano = info.get("score_plano", True)
            icono = "🟡" if score_plano else "🟢"
            status = "Score plano (5.0)" if score_plano else "Con datos"
            fragil_tag = " ⚠" if info.get("fragil") else ""
            filas += f"<tr><td>{icono} {escape(nid)}{fragil_tag}</td><td>{escape(status)}</td><td colspan='2' style='text-align:center;color:var(--text-secondary);'>modo standalone</td></tr>"
        return f"""<div class="historial-box">
      <h3>Cobertura de Datos</h3>
      {alerta_ban}
      <p style="margin-bottom:12px;">{con_datos}/9 nodos con datos reales ({sin_datos} con score plano &mdash; sin items cargados)</p>
      <table class="tabla-historial">
        <tr><th>Nodo</th><th>Estado</th><th>Items totales</th><th>Items relevantes</th></tr>
        {filas}
      </table>
    </div>"""
    filas = ""
    con_datos = 0
    sin_datos = 0
    for nid in NODOS_CULTURALES:
        info = brechas.get(nid, {})
        total = info.get("total_items", 0)
        relevantes = info.get("items_relevantes", 0)
        score_plano = info.get("score_plano", False)
        if score_plano or (total == 0):
            icono = "🔴"
            status = "Sin datos"
            sin_datos += 1
        elif relevantes < 3:
            icono = "🟡"
            status = "Pocos datos"
            sin_datos += 1
        else:
            icono = "🟢"
            status = "OK"
            con_datos += 1
        fragil_tag = " ⚠" if info.get("fragil") else ""
        filas += f"<tr><td>{icono} {escape(nid)}{fragil_tag}</td><td>{escape(status)}</td><td>{total}</td><td>{relevantes}</td></tr>"
    return f"""<div class="historial-box">
    <h3>Cobertura de Datos</h3>
    {alerta_ban}
    <p style="margin-bottom:12px;">{con_datos}/9 nodos con datos suficientes ({sin_datos} con d&eacute;ficit)</p>
    <table class="tabla-historial">
      <tr><th>Nodo</th><th>Estado</th><th>Items totales</th><th>Items relevantes</th></tr>
      {filas}
    </table>
  </div>"""


TEMPLATE_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Informe Topol&oacute;gico: {sociedad}</title>
<style>{css}</style>
</head>
<body>
<div class="container">
{cabecera}
{portada}
{tres_columnas}
{formas_complejas}
{dos_columnas}
{graficos}
{historial}
{alertas}
{mirada}
{cobertura}
<div class="footer">
  Generado por Topolog&iacute;a Social &mdash; Sistema multi-agente de observaci&oacute;n cultural
</div>
</div>
</body>
</html>"""


def generar_informe_html(
    sociedad: str = "Chile",
    estado: EstadoCultural | None = None,
    operaciones: list[OperacionCinetica] | None = None,
    especulaciones: list[Especulacion] | None = None,
    estudios: list[Estudio] | None = None,
    items_por_nodo: dict[str, list[ItemInformativo]] | None = None,
    informe_redactor: InformeDiario | None = None,
    brechas: dict[str, dict] | None = None,
) -> str:
    store = FileStore()
    if estado is None:
        estado = store.cargar_estado(sociedad)
    if estado is None:
        return ""

    if operaciones is None:
        operaciones = detectar_operaciones(estado)

    if items_por_nodo:
        items_por_nodo = {k: _filtrar_fuentes(v) for k, v in items_por_nodo.items()}

    if brechas is None:
        brechas = detectar_brechas(estado=estado, items_por_nodo=items_por_nodo)

    fecha = estado.fecha.strftime("%Y-%m-%d %H:%M")

    html = TEMPLATE_PAGE \
        .replace("{css}", CSS) \
        .replace("{sociedad}", escape(sociedad)) \
        .replace("{cabecera}", _build_cabecera(sociedad, fecha)) \
        .replace("{portada}", _build_portada(estado, informe_redactor)) \
        .replace("{tres_columnas}", _build_tres_columnas(estado, informe_redactor, items_por_nodo)) \
        .replace("{formas_complejas}", _build_formas_complejas(estado)) \
        .replace("{dos_columnas}", _build_dos_columnas(especulaciones, estudios, operaciones)) \
        .replace("{graficos}", _build_graficos()) \
        .replace("{historial}", _build_historial(sociedad)) \
        .replace("{alertas}", _build_alertas(informe_redactor)) \
        .replace("{mirada}", _build_mirada(informe_redactor)) \
        .replace("{cobertura}", _build_cobertura(brechas))

    ruta = get_reportes_dir()
    ruta.mkdir(parents=True, exist_ok=True)
    archivo = ruta / f"informe_{sociedad}_{datetime.now().strftime('%Y-%m-%d_%H%M')}.html"
    archivo.write_text(html, encoding="utf-8")
    return str(archivo)
