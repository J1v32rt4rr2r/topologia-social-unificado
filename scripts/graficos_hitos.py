from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from topologia.paths import get_reportes_dir

# ── Config visual ──────────────────────────────────────────────────────

plt.rcParams["figure.facecolor"] = "#0a0a0a"
plt.rcParams["axes.facecolor"] = "#0a0a0a"
plt.rcParams["text.color"] = "#e0e0e0"
plt.rcParams["axes.labelcolor"] = "#e0e0e0"
plt.rcParams["xtick.color"] = "#e0e0e0"
plt.rcParams["ytick.color"] = "#e0e0e0"
plt.rcParams["axes.edgecolor"] = "#333"
plt.rcParams["grid.color"] = "#222"

NODOS = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]

COLOR_PERIODOS = {
    "estallido_2019": "#ff6b35",
    "pandemia_ola1_2020": "#00d4ff",
    "pandemia_ola2_2021": "#c084fc",
    "temporal_julio_2026": "#ffd700",
    "plebiscito_2020": "#ff4444",
    "estallido_nocturno_2020": "#44ff88",
    "plebiscito_1988": "#aaaaaa",
}

COLOR_M_L_S = {"m": "#00d4ff", "l": "#c084fc", "s": "#ff6b35"}
ETIQUETAS_M_L_S = {"m": "M_m (Material)", "l": "M_l (Lógico-valórico)", "s": "M_s (Social)"}

CONFIG_HITOS = Path(__file__).resolve().parent.parent / "config" / "hitos.yaml"
REPORTES_DIR = get_reportes_dir()


def cargar_hitos() -> list[dict]:
    with open(CONFIG_HITOS, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _label(pid: str) -> str:
    m = {
        "estallido_2019": "Estallido 2019",
        "pandemia_ola1_2020": "Pandemia 2020",
        "pandemia_ola2_2021": "Pandemia 2021",
        "temporal_julio_2026": "Temporal Jul 2026",
        "plebiscito_2020": "Plebiscito 2020",
        "estallido_nocturno_2020": "Estallido Noct 2020",
        "plebiscito_1988": "Plebiscito 1988",
    }
    return m.get(pid, pid)


# ── Gráfico 1: Delta por nodo (barras agrupadas) ──────────────────────

def grafico_delta_nodos(hitos: list[dict], path: Path):
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_facecolor("#0a0a0a")

    x = np.arange(len(NODOS))
    w = 0.25

    for i, h in enumerate(hitos):
        deltas = [h["nodos"][n]["delta"] for n in NODOS]
        offset = (i - 1) * w
        bars = ax.bar(x + offset, deltas, w, label=_label(h["id"]),
                      color=COLOR_PERIODOS.get(h["id"], "#888"), alpha=0.85,
                      edgecolor="white", linewidth=0.5)
        for bar, d in zip(bars, deltas):
            if d > 1:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        f"{d:.1f}", ha="center", va="bottom", fontsize=6, fontweight="bold",
                        color="#e0e0e0")

    ax.axhline(y=0, color="#444", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(NODOS, fontsize=9)
    ax.set_ylabel("δ (grados) — Divergencia angular", fontsize=11)
    ax.set_title("δ POR NODO EN CADA PERIODO HISTÓRICO", fontsize=14, fontweight="bold", color="#e0e0e0", pad=15)
    ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")
    ax.grid(True, axis="y", alpha=0.15, color="#444")

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 2: Evolución M/L/S por nodo (subplots 3×3) ────────────────

def grafico_evolucion_dimensional(hitos: list[dict], path: Path):
    ids = [h["id"] for h in hitos]
    labels = [_label(i) for i in ids]
    fig, axes = plt.subplots(3, 3, figsize=(16, 12))
    fig.suptitle("EVOLUCIÓN DIMENSIONAL POR NODO (M_m · M_l · M_s)", fontsize=14, fontweight="bold", color="#e0e0e0", y=0.98)

    for idx, nodo in enumerate(NODOS):
        ax = axes[idx // 3][idx % 3]
        ax.set_facecolor("#0a0a0a")

        m_vals = [h["nodos"][nodo]["m"] for h in hitos]
        l_vals = [h["nodos"][nodo]["l"] for h in hitos]
        s_vals = [h["nodos"][nodo]["s"] for h in hitos]

        xs = range(len(hitos))
        ax.plot(xs, m_vals, "o-", color=COLOR_M_L_S["m"], lw=2.5, markersize=8, label="M_m")
        ax.plot(xs, l_vals, "s-", color=COLOR_M_L_S["l"], lw=2.5, markersize=8, label="M_l")
        ax.plot(xs, s_vals, "^-", color=COLOR_M_L_S["s"], lw=2.5, markersize=8, label="M_s")

        for i in range(len(hitos)):
            ax.text(i, m_vals[i] + 0.15, f"{m_vals[i]:.1f}", ha="center", fontsize=7, color=COLOR_M_L_S["m"])
            ax.text(i, l_vals[i] + 0.15, f"{l_vals[i]:.1f}", ha="center", fontsize=7, color=COLOR_M_L_S["l"])
            ax.text(i, s_vals[i] + 0.15, f"{s_vals[i]:.1f}", ha="center", fontsize=7, color=COLOR_M_L_S["s"])

        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylim(0, 10)
        ax.set_title(nodo, fontsize=13, fontweight="bold", color="#e0e0e0", pad=8)
        ax.grid(True, alpha=0.15, color="#444")
        if idx == 0:
            ax.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 3: Radar comparativo ──────────────────────────────────────

def grafico_radar_comparativo(hitos: list[dict], path: Path):
    N = len(NODOS)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection="polar"))
    ax.set_facecolor("#0a0a0a")

    for h in hitos:
        vals = [h["nodos"][n]["delta"] for n in NODOS]
        vals += vals[:1]
        color = COLOR_PERIODOS.get(h["id"], "#888")
        ax.plot(angles, vals, "o-", lw=2.5, color=color, label=_label(h["id"]), markersize=8)
        ax.fill(angles, vals, alpha=0.08, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(NODOS, fontsize=9)
    ax.set_ylim(0, max(max(h["nodos"][n]["delta"] for n in NODOS) for h in hitos) * 1.3)
    ax.set_title("δ POR NODO — RADAR COMPARATIVO", fontsize=14, fontweight="bold", color="#e0e0e0", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=10,
              facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")
    ax.grid(True, alpha=0.3, color="#444")

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 4: Mapa de calor (nodos × periodos) ───────────────────────

def grafico_mapa_calor(hitos: list[dict], path: Path):
    ids = [h["id"] for h in hitos]
    data = np.zeros((len(NODOS), len(hitos)))
    for i, n in enumerate(NODOS):
        for j, h in enumerate(hitos):
            data[i, j] = h["nodos"][n]["delta"]

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.set_facecolor("#0a0a0a")

    vmax = data.max() if data.max() > 0 else 10
    im = ax.imshow(data, cmap="inferno", aspect="auto", vmin=0, vmax=vmax)

    for i in range(len(NODOS)):
        for j in range(len(hitos)):
            v = data[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                    fontsize=11, fontweight="bold",
                    color="white" if v < vmax * 0.6 else "#111")

    ax.set_xticks(range(len(hitos)))
    ax.set_xticklabels([_label(i) for i in ids], fontsize=10)
    ax.set_yticks(range(len(NODOS)))
    ax.set_yticklabels(NODOS, fontsize=10)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("δ (grados)", rotation=270, labelpad=20, color="white")
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="white")

    ax.set_title("MAPA DE CALOR — δ POR NODO Y PERIODO", fontsize=14, fontweight="bold", color="#e0e0e0", pad=15)

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 5: Top nodos más volátiles ─────────────────────────────────

def grafico_volatilidad(hitos: list[dict], path: Path):
    volatil = {}
    for n in NODOS:
        deltas = [h["nodos"][n]["delta"] for h in hitos]
        volatil[n] = max(deltas) - min(deltas)

    sorted_nodos = sorted(volatil, key=volatil.get, reverse=True)
    sorted_vals = [volatil[n] for n in sorted_nodos]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_facecolor("#0a0a0a")

    colors = [plt.cm.plasma(v / max(sorted_vals)) for v in sorted_vals] if max(sorted_vals) > 0 else ["#888"] * len(sorted_vals)
    bars = ax.barh(range(len(sorted_nodos)), sorted_vals, color=colors, edgecolor="white", linewidth=0.5, height=0.6)

    for i, (n, v) in enumerate(zip(sorted_nodos, sorted_vals)):
        deltas_str = " → ".join(f"{h['nodos'][n]['delta']:.1f}°" for h in hitos)
        ax.text(v + 0.2, i, f"Δ{v:.1f}°  ({deltas_str})", va="center", fontsize=8, color="#e0e0e0")

    ax.set_yticks(range(len(sorted_nodos)))
    ax.set_yticklabels(sorted_nodos, fontsize=10)
    ax.set_xlabel("Rango de δ (max - min)", fontsize=11)
    ax.set_title("VOLATILIDAD POR NODO — Variación de δ entre periodos", fontsize=14, fontweight="bold", color="#e0e0e0", pad=15)
    ax.invert_yaxis()
    ax.grid(True, axis="x", alpha=0.15, color="#444")

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── HTML Report ────────────────────────────────────────────────────────

def generar_html(hitos: list[dict]) -> str:
    def delta_color(d):
        if d >= 10:
            return "#ff4444"
        if d >= 5:
            return "#ffd700"
        return "#44ff88"

    rows = ""
    for n in NODOS:
        cels = ""
        for h in hitos:
            nd = h["nodos"][n]
            dc = delta_color(nd["delta"])
            cels += f'<td style="color:{dc}">{nd["delta"]:.1f}°</td>'
        rows += f"<tr><td>{n}</td>{cels}</tr>"

    periodos_html = ""
    for h in hitos:
        pid = h["id"]
        est = h["estado"]
        periodos_html += f"""
        <div class="periodo-card" style="border-left:4px solid {COLOR_PERIODOS.get(pid, '#888')}">
            <h3>{_label(pid)}</h3>
            <div class="periodo-meta">{h['periodo']['inicio']} → {h['periodo']['fin']} · {h['recoleccion']['total_items']} items</div>
            <div class="periodo-stats">
                <span>δ = {est['delta_promedio']}°</span>
                <span>M = ({est['M_m']}, {est['M_l']}, {est['M_s']})</span>
                <span>θ = {est['theta_cultura']}°</span>
                <span>Tensión = {est['tension_total']}</span>
                <span>Era k = {est['era_k']}</span>
                <span>Ops: {', '.join(est['operaciones']) if est['operaciones'] else '—'}</span>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Hitos Históricos — Topología Social</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a0a; color:#e0e0e0; font-family:'Segoe UI',system-ui,sans-serif; padding:30px; }}
  h1 {{ color:#ffd700; font-size:1.6em; margin-bottom:5px; }}
  .sub {{ color:#888; font-size:0.9em; margin-bottom:25px; }}
  .section {{ margin:35px 0 15px; padding-bottom:5px; border-bottom:1px solid #333; color:#ffd700; font-size:1.2em; }}
  img {{ width:100%; max-width:1100px; border-radius:6px; border:1px solid #333; margin:15px 0; display:block; }}
  table {{ border-collapse:collapse; width:100%; font-size:0.9em; margin:20px 0; }}
  th, td {{ border:1px solid #333; padding:8px 12px; text-align:center; }}
  th {{ background:#1a1a1a; color:#aaa; font-weight:600; }}
  .periodo-card {{ background:#141414; border-radius:8px; padding:14px 18px; margin:12px 0; }}
  .periodo-meta {{ color:#888; font-size:0.85em; margin:4px 0 10px; }}
  .periodo-stats {{ display:flex; gap:12px; flex-wrap:wrap; font-size:0.85em; }}
  .periodo-stats span {{ background:#1a1a1a; padding:4px 10px; border-radius:4px; }}
</style>
</head>
<body>
<h1>HITOS HISTÓRICOS — Análisis Cultural Comparativo</h1>
<div class="sub">{len(hitos)} períodos · {len(NODOS)} nodos culturales</div>

<div class="section">Períodos</div>
{periodos_html}

<div class="section">📊 δ por Nodo</div>
<img src="hito_delta_nodos.png" alt="Delta por nodo">

<div class="section">📈 Evolución Dimensional por Nodo</div>
<img src="hito_evolucion_dimensional.png" alt="Evolución dimensional">

<div class="section">🎯 Radar Comparativo</div>
<img src="hito_radar.png" alt="Radar comparativo">

<div class="section">🗺️ Mapa de Calor</div>
<img src="hito_mapa_calor.png" alt="Mapa de calor">

<div class="section">⚡ Volatilidad</div>
<img src="hito_volatilidad.png" alt="Volatilidad">

<div class="section">📋 Tabla de δ por Nodo</div>
<table>
  <tr><th>Nodo</th>{"".join(f"<th>{_label(h['id'])}</th>" for h in hitos)}</tr>
  {rows}
</table>

<div class="sub" style="margin-top:30px;text-align:center;color:#555;font-size:0.8em">
  Generado el · Topología Social
</div>
</body>
</html>"""


# ── Generar todo ───────────────────────────────────────────────────────

def generar_todos(salida: Path | None = None) -> list[Path]:
    if salida is None:
        salida = REPORTES_DIR
    salida.mkdir(parents=True, exist_ok=True)

    hitos = cargar_hitos()
    if not hitos:
        print("No hay hitos cargados.")
        return []

    archivos = [
        ("hito_delta_nodos.png", grafico_delta_nodos),
        ("hito_evolucion_dimensional.png", grafico_evolucion_dimensional),
        ("hito_radar.png", grafico_radar_comparativo),
        ("hito_mapa_calor.png", grafico_mapa_calor),
        ("hito_volatilidad.png", grafico_volatilidad),
    ]

    paths = []
    for name, fn in archivos:
        p = salida / name
        fn(hitos, p)
        paths.append(p)
        print(f"  {name}")

    html = generar_html(hitos)
    (salida / "hitos.html").write_text(html, encoding="utf-8")
    print(f"  hitos.html")

    return paths


def main():
    print("Generando gráficos de hitos históricos...")
    archivos = generar_todos()
    print(f"\n{len(archivos)} gráficos generados en: {REPORTES_DIR}")
    for a in archivos:
        print(f"  {a.name}  ({a.stat().st_size / 1024:.0f} KB)")
    print(f"  hitos.html")


if __name__ == "__main__":
    main()
