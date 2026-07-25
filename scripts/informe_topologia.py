"""Genera informe_topologia.html integrando estado, riesgo, hitos y timeline."""

import json
import shutil
from pathlib import Path

DATA = Path.home() / ".local" / "share" / "topologia-social" / "data"
DESKTOP = Path.home() / "Desktop"

CSS = """
:root {
  --bg: #f5f6fa; --card-bg: #fff; --text: #1a1a2e;
  --text-sec: #555; --accent: #e94560; --accent2: #0f3460;
  --green: #2ecc71; --yellow: #f39c12; --red: #e74c3c;
  --blue: #3498db; --border: #e0e0e0;
  --shadow: 0 2px 12px rgba(0,0,0,0.08); --radius: 12px;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family:'Georgia','Times New Roman',serif; font-size:17px;
  line-height:1.7; color:var(--text); background:var(--bg);
}
.container { max-width:1200px; margin:0 auto; padding:20px; }
.header {
  text-align:center; padding:40px 20px 30px;
  border-bottom:3px double var(--accent2); margin-bottom:28px;
}
.header h1 {
  font-family:'Segoe UI',system-ui,sans-serif; font-size:42px;
  font-weight:800; color:var(--accent2); letter-spacing:4px;
  text-transform:uppercase; margin-bottom:6px;
}
.header .subtitle { font-size:18px; color:var(--text-sec); font-style:italic; }
.header .fecha { font-size:16px; color:var(--text-sec); margin-top:8px; }
.portada-box {
  background:linear-gradient(135deg,var(--accent2),#16213e); color:#fff;
  border-radius:var(--radius); padding:32px 40px; margin-bottom:28px;
  display:grid; grid-template-columns:auto 1fr auto; gap:24px; align-items:center;
}
.portada-box.amarilla { background:linear-gradient(135deg,#b7950b,#d4ac0d); }
.portada-box.roja { background:linear-gradient(135deg,#922b21,#c0392b); }
.portada-box.verde { background:linear-gradient(135deg,#1e8449,#27ae60); }
.portada-metrica-principal { text-align:center; }
.portada-metrica-principal .valor { font-size:56px; font-weight:800; line-height:1; }
.portada-metrica-principal .label { font-size:14px; opacity:0.7; margin-top:4px; }
.portada-metrica-secundaria { display:flex; gap:16px; flex-wrap:wrap; }
.portada-metrica-secundaria .item {
  background:rgba(255,255,255,0.1); padding:8px 16px;
  border-radius:8px; font-size:15px;
}
.portada-metrica-secundaria .item strong { font-size:20px; }
.portada-resumen {
  font-size:18px; font-style:italic; line-height:1.6;
  max-width:400px; border-left:3px solid rgba(255,255,255,0.3); padding-left:20px;
}
.card {
  background:var(--card-bg); border-radius:var(--radius);
  padding:24px; box-shadow:var(--shadow); margin-bottom:20px;
}
.card h2 {
  font-family:'Segoe UI',system-ui,sans-serif; font-size:24px;
  color:var(--accent2); margin-bottom:16px; padding-bottom:8px;
  border-bottom:2px solid var(--border);
}
.text-block { font-size:16px; line-height:1.8; color:var(--text); margin-bottom:12px; white-space:pre-wrap; }
table { width:100%; border-collapse:collapse; margin:12px 0; }
th, td { padding:10px 14px; text-align:left; border-bottom:1px solid var(--border); font-size:15px; }
th { background:#f0f4ff; font-weight:700; color:var(--accent2); }
tr:hover { background:#fafbfe; }
.alto { color:var(--red); font-weight:700; }
.medio { color:var(--yellow); font-weight:600; }
.bajo { color:var(--green); }
.riesgo-bar-wrap { display:flex; align-items:center; gap:12px; margin:6px 0; }
.riesgo-bar {
  flex:1; height:24px; background:#ecf0f1; border-radius:12px; overflow:hidden;
}
.riesgo-bar-fill {
  height:100%; border-radius:12px; transition:width 0.3s;
}
.riesgo-val { min-width:60px; text-align:right; font-size:15px; font-weight:600; }
.alerta-badge {
  display:inline-block; padding:4px 16px; border-radius:20px;
  font-size:13px; font-weight:700; text-transform:uppercase;
}
.alerta-badge.amarilla { background:#fef3cd; color:#856404; border:1px solid #ffc107; }
.alerta-badge.roja { background:#f8d7da; color:#721c24; border:1px solid #f5c6cb; }
.alerta-badge.verde { background:#d4edda; color:#155724; border:1px solid #c3e6cb; }
.dos-columnas { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
@media (max-width:900px) {
  .dos-columnas { grid-template-columns:1fr; }
  .portada-box { grid-template-columns:1fr; text-align:center; }
  .portada-resumen { border-left:none; border-top:3px solid rgba(255,255,255,0.3); padding-left:0; padding-top:16px; max-width:none; }
}
.footer {
  text-align:center; padding:24px; font-size:14px;
  color:var(--text-sec); border-top:1px solid var(--border); margin-top:28px;
}
.subida { color:var(--red); } .bajada { color:var(--green); } .estable { color:var(--text-sec); }
"""

def color_alerta(r):
    if r >= 0.8: return "roja"
    if r >= 0.5: return "amarilla"
    return "verde"

def color_riesgo(v):
    if v >= 0.8: return "var(--red)"
    if v >= 0.5: return "var(--yellow)"
    return "var(--green)"

def barra(v, label):
    pct = int(v * 100)
    c = color_riesgo(v)
    return f'<div class="riesgo-bar-wrap"><span style="min-width:160px;font-size:14px;">{label}</span><div class="riesgo-bar"><div class="riesgo-bar-fill" style="width:{pct}%;background:{c};"></div></div><span class="riesgo-val">{v:.4f}</span></div>'

def badge_html(alerta):
    a = alerta.lower()
    if "amarill" in a or a == "yellow": return '<span class="alerta-badge amarilla">AMARILLA</span>'
    if "roj" in a or a == "red": return '<span class="alerta-badge roja">ROJA</span>'
    return '<span class="alerta-badge verde">VERDE</span>'

def delta_icon(d):
    if d > 0: return f'<span class="subida">⬆ +{d:.1f}°</span>'
    if d < 0: return f'<span class="bajada">⬇ {d:.1f}°</span>'
    return f'<span class="estable">→ 0°</span>'

def main(sociedad="Chile"):
    estados_dir = DATA / "estados"
    reportes_json_dir = DATA / "reportes_json"
    redes_dir = DATA / "reportes" / "redes_riesgo"
    reportes_dir = DATA / "reportes"

    archivos_estado = sorted([f for f in estados_dir.glob(f"{sociedad}_*.json")])
    if not archivos_estado:
        print(f"No hay estados para {sociedad}")
        return
    ultimo_archivo = archivos_estado[-1]
    fecha_tag = ultimo_archivo.stem.replace(f"{sociedad}_", "")

    with open(ultimo_archivo, encoding="utf-8") as f:
        estado = json.load(f)

    sintesis = {}
    sintesis_path = reportes_json_dir / f"{sociedad}_{fecha_tag}.json"
    if sintesis_path.exists():
        with open(sintesis_path, encoding="utf-8") as f:
            sintesis = json.load(f)

    riesgo = {}
    riesgo_path = DATA / "riesgo_actual.json"
    if riesgo_path.exists():
        with open(riesgo_path, encoding="utf-8") as f:
            riesgo = json.load(f)

    red_data = {}
    redes = sorted(redes_dir.glob("red_riesgo_*.json"))
    if redes:
        with open(redes[-1], encoding="utf-8") as f:
            red_data = json.load(f)

    hitos = []
    resumen_path = reportes_dir / "resumen.json"
    if resumen_path.exists():
        with open(resumen_path, encoding="utf-8") as f:
            hitos = json.load(f)

    distancias = {}
    dist_path = reportes_dir / "distancias.json"
    if dist_path.exists():
        with open(dist_path, encoding="utf-8") as f:
            distancias = json.load(f)

    # Calibration via orchestrator
    from topologia.orchestrator import Orchestrator
    from topologia.storage.store import FileStore
    from topologia.models.schemas import EstadoCultural

    store = FileStore()
    estado_obj = store.cargar_estado(sociedad)
    calib = {"mas_similar": None, "ranking": [], "nodos_destacados": []}
    if estado_obj:
        orch = Orchestrator()
        calib = orch.calibrar(estado_obj)

    # Build HTML
    lines = []
    a = _a = lines.append

    a('<!DOCTYPE html><html lang="es"><head>')
    a('<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">')
    a(f"<title>Informe Topología: {sociedad}</title><style>{CSS}</style></head><body>")
    a('<div class="container">')

    # Header
    a('<div class="header">')
    a('<h1>Informe Topología</h1>')
    a(f'<div class="subtitle">Observación cultural de {sociedad}</div>')
    a(f'<div class="fecha">{fecha_tag}</div>')
    a('</div>')

    # Portada
    r_val = riesgo.get("R_compuesto", 0)
    alerta = riesgo.get("alerta", "VERDE")
    clase_portada = color_alerta(r_val)
    a(f'<div class="portada-box {clase_portada}">')
    a(f'<div class="portada-metrica-principal"><div class="valor">{estado.get("delta_promedio",0):.1f}°</div><div class="label">δ desviación</div></div>')
    m = f'M=({estado["M_m"]:.1f},{estado["M_l"]:.1f},{estado["M_s"]:.1f})'
    sec = [
        ("M", m),
        ("θ", f'{estado.get("theta_cultura",0):.1f}°'),
        ("Era k", str(estado.get("era_k","?"))),
        ("Coherencia", f'{estado.get("coherencia_interna",0):.1f}°'),
    ]
    a('<div class="portada-metrica-secundaria">')
    for lbl, val in sec:
        a(f'<div class="item"><strong>{val}</strong><br>{lbl}</div>')
    a('</div>')
    a(f'<div class="portada-resumen">R compuesto: {r_val:.4f} {badge_html(alerta)}</div>')
    a('</div>')

    # Resumen ejecutivo
    if sintesis.get("resumen_ejecutivo"):
        a('<div class="card">')
        a('<h2>Resumen Ejecutivo</h2>')
        a(f'<div class="text-block">{sintesis["resumen_ejecutivo"]}</div>')
        a('</div>')

    # Panorama
    if sintesis.get("panorama"):
        a('<div class="card">')
        a('<h2>Panorama General</h2>')
        a(f'<div class="text-block">{sintesis["panorama"]}</div>')
        a('</div>')

    # Dinámicas
    if sintesis.get("dinamicas"):
        a('<div class="card">')
        a('<h2>Dinámicas Detectadas</h2>')
        a(f'<div class="text-block">{sintesis["dinamicas"]}</div>')
        a('</div>')

    # Riesgo Escalar
    a('<div class="card">')
    a(f'<h2>Riesgo Escalar R {badge_html(alerta)}</h2>')
    a(f'<p style="margin-bottom:12px;">R compuesto = <strong>{r_val:.4f}</strong> — {alerta}</p>')
    desg = riesgo.get("desglose", {})
    NOMBRES = {
        "theta_desviacion": "θ desviación (dirección cultural)",
        "v_trabajo_norm": "v Trabajo (velocidad laboral)",
        "m_contraccion": "M contracción (base material)",
        "delta_proximidad": "δ proximidad (cercanía a hitos)",
        "co_sincronia": "co_sincronía (acoplamiento nodal)",
        "s_activacion": "S activación (nodos sensibles)",
    }
    for k in ["theta_desviacion","v_trabajo_norm","m_contraccion","delta_proximidad","co_sincronia","s_activacion"]:
        if k in desg:
            a(barra(desg[k], NOMBRES.get(k, k)))
    # Nodos destacados del riesgo
    nd = riesgo.get("nodos_destacados", [])
    if nd:
        a('<p style="margin-top:16px;font-weight:700;">Nodos en alerta por el escalar:</p>')
        for n in nd:
            a(f'<p style="color:var(--red);margin:4px 0;">⚠️ {n["nodo"]}: δ={n["delta"]}</p>')
    a('</div>')

    # Calibración histórica
    a('<div class="card">')
    a('<h2>Calibración Histórica</h2>')
    ms = calib.get("mas_similar")
    if ms:
        a(f'<p><strong>Hito más similar:</strong> {ms["id"]} (r={ms["correlacion"]:.3f}, MAE={ms["mae"]}°)</p>')
        a(f'<p style="margin-bottom:12px;color:var(--text-sec);">{ms.get("descripcion","")}</p>')
        a('<table><tr><th>#</th><th>Hito</th><th>r</th><th>MAE</th></tr>')
        for i, rnk in enumerate(calib.get("ranking", [])[:7], 1):
            a(f'<tr><td>{i}</td><td>{rnk["id"]}</td><td>{rnk["correlacion"]:+.3f}</td><td>{rnk["mae"]}°</td></tr>')
        a('</table>')
        nd = calib.get("nodos_destacados", [])
        if nd:
            a('<p style="font-weight:700;margin-top:12px;">Nodos con divergencia >3° respecto al hito:</p>')
            for n in nd:
                cls = "alto" if n["etiqueta"] == "ALERTA" else "medio"
                a(f'<p class="{cls}">{"🔴" if n["etiqueta"]=="ALERTA" else "🟡"} {n["nodo"]}: actual={n["delta_actual"]}° vs hito={n["delta_hito"]}° (dif={n["diferencia"]:+}°)</p>')
    else:
        a("<p>No hay hitos registrados para comparar.</p>")
    a('</div>')

    # Estado actual (tabla nodos)
    a('<div class="card">')
    a('<h2>Estado por Nodo</h2>')
    a('<table><tr><th>Nodo</th><th>M_m</th><th>M_l</th><th>M_s</th><th>δ</th><th>Alerta</th></tr>')
    for n in estado.get("nodos", []):
        d = n.get("delta", 0)
        cls = "alto" if d >= 10 else ("medio" if d >= 5 else "bajo")
        alert_icon = "🔴" if d >= 10 else ("🟡" if d >= 5 else "🟢")
        a(f'<tr><td><strong>{n["nodo_id"]}</strong></td><td>{n["dimension_m"]}</td><td>{n["dimension_l"]}</td><td>{n["dimension_s"]}</td><td class="{cls}">{d:.1f}°</td><td>{alert_icon}</td></tr>')
    a('</table>')
    a('</div>')

    # Timeline 14 días
    ts = red_data.get("time_series", {})
    fechas = ts.get("fechas", [])
    valores = ts.get("valores", [])
    if fechas:
        a('<div class="card">')
        a('<h2>Evolución Temporal (14 días)</h2>')
        nodos_ts = list(valores[0].keys()) if valores else []
        a('<div style="overflow-x:auto;">')
        a('<table><tr><th>Fecha</th><th>δ prom</th>')
        for nid in nodos_ts:
            a(f'<th>{nid[:6]}..</th>')
        a('</tr>')
        for i, fch in enumerate(fechas):
            v = valores[i] if i < len(valores) else {}
            vals = [v.get(nid, 0) for nid in nodos_ts]
            d_prom = sum(vals) / len(vals) if vals else 0
            a(f'<tr><td>{fch[:10]}</td><td><strong>{d_prom:.1f}°</strong></td>')
            for vi in vals:
                cls = "alto" if vi >= 10 else ("medio" if vi >= 5 else "bajo")
                a(f'<td class="{cls}">{vi:.1f}</td>')
            a('</tr>')
        a('</table></div>')
        a('</div>')

    # Mirada hacia adelante
    if sintesis.get("mirada_adelante"):
        a('<div class="card">')
        a('<h2>Mirada hacia Adelante</h2>')
        a(f'<div class="text-block">{sintesis["mirada_adelante"]}</div>')
        # Interpretación del escalar
        a('<div style="margin-top:16px;padding:16px;background:#fef9e7;border-left:4px solid var(--yellow);border-radius:4px;">')
        a('<strong style="color:#856404;">🔮 Proyección de crisis desde el escalar:</strong><br>')
        puntos = []
        if desg.get("theta_desviacion", 0) > 0.7:
            puntos.append("θ desviación al máximo: la dirección cultural se ha desalineado fuertemente — riesgo de reconfiguración estructural.")
        if desg.get("v_trabajo_norm", 0) > 0.7:
            puntos.append("Velocidad de TRABAJO en máximo: el nodo laboral está en movimiento acelerado, posible precursor de crisis.")
        if desg.get("m_contraccion", 0) > 0.7:
            puntos.append("Contracción de M elevada: la base material se reduce, aumentando vulnerabilidad del sistema.")
        if desg.get("s_activacion", 0) > 0.3:
            puntos.append("Nodos sensibles activados — SEXUALIDAD puede amplificar cualquier perturbación entrante.")
        if not puntos:
            puntos.append("Sin señales de crisis inminente. R en zona de vigilancia.")
        for p in puntos:
            a(f'<p style="margin:6px 0;font-size:15px;">• {p}</p>')
        a('</div>')
        a('</div>')

    # Especulaciones y estudios
    if sintesis.get("especulaciones_y_estudios"):
        a('<div class="card">')
        a('<h2>Especulaciones y Estudios</h2>')
        a(f'<div class="text-block">{sintesis["especulaciones_y_estudios"]}</div>')
        a('</div>')

    # Hitos históricos comparativa
    if hitos:
        a('<div class="card">')
        a('<h2>Hitos Históricos (Referencia)</h2>')
        a('<table><tr><th>Hito</th><th>Tipo</th><th>δ</th><th>M_m</th><th>M_l</th><th>M_s</th><th>θ</th><th>Tensión</th></tr>')
        for h in hitos:
            a(f'<tr><td><strong>{h["id"]}</strong></td><td>{h["tipo"]}</td><td>{h["delta_promedio"]}°</td><td>{h["M_m"]}</td><td>{h["M_l"]}</td><td>{h["M_s"]}</td><td>{h["theta_cultura"]}°</td><td>{h["tension_total"]}</td></tr>')
        a('</table>')
        a('</div>')

    # Alertas del Árbitro
    alertas_sint = sintesis.get("alertas", [])
    if alertas_sint:
        a('<div class="card">')
        a('<h2>Alertas</h2>')
        for al in alertas_sint:
            tip = al.get("tipo", "info")
            a(f'<div style="padding:12px 16px;margin:8px 0;background:#f8d7da;border-left:4px solid var(--red);border-radius:4px;font-size:15px;"><strong>[{tip.upper()}]</strong> {al.get("mensaje","")}</div>')
        a('</div>')

    # Dashboard
    dash = sintesis.get("dashboard", {})
    if dash:
        a('<div class="card">')
        a('<h2>Dashboard</h2>')
        a(f'<p><strong>Métrica principal:</strong> {dash.get("metrica_principal","")}</p>')
        a(f'<p><strong>Cambio clave:</strong> {dash.get("cambio_clave","")}</p>')
        crit = dash.get("nodos_criticos", [])
        if crit:
            a(f'<p><strong>Nodos críticos:</strong> {", ".join(crit)}</p>')
        a('</div>')

    # Footer
    a('<div class="footer">')
    a('Generado por Topología Social — Sistema multi-agente de observación cultural')
    a('<br><span style="font-size:12px;">Informe integrado: estado, riesgo escalar R, calibración histórica y proyección</span>')
    a('</div>')
    a('</div></body></html>')

    html = "\n".join(lines)

    destino = DESKTOP / "informe_topologia.html"
    with open(destino, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Informe generado: {destino}")
    print(f"Tamaño: {len(html)} bytes")
    print(f"R={r_val:.4f} ({alerta}) | δ={estado.get('delta_promedio',0):.1f}° | Hito: {ms['id'] if ms else 'N/A'}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sociedad", default="Chile")
    args = parser.parse_args()
    main(args.sociedad)
