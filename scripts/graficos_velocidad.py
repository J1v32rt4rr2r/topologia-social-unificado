from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from topologia.paths import get_reportes_dir

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

COLOR_HITOS = {
    "estallido_2019": "#ff6b35",
    "pandemia_ola1_2020": "#00d4ff",
    "pandemia_ola2_2021": "#c084fc",
    "temporal_julio_2026": "#ffd700",
    "plebiscito_2020": "#ff4444",
    "estallido_nocturno_2020": "#44ff88",
}

LABEL_HITO = {
    "estallido_2019": "Estallido 2019",
    "pandemia_ola1_2020": "Pandemia O1 2020",
    "pandemia_ola2_2021": "Pandemia O2 2021",
    "temporal_julio_2026": "Temporal Jul 2026",
    "plebiscito_2020": "Plebiscito 2020",
    "estallido_nocturno_2020": "Estallido Noct 2020",
}

CONFIG_HITOS = Path(__file__).resolve().parent.parent / "config" / "hitos.yaml"
REPORTES_DIR = get_reportes_dir()


def cargar_hitos() -> list[dict]:
    with open(CONFIG_HITOS, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def hitos_con_serie(hitos: list[dict]) -> list[dict]:
    return [h for h in hitos if h.get("serie") and len(h["serie"]) >= 2]


# ── Gráfico 1: δ(t) por nodo (3x3 subplots, cada nodo = 1 plot) ─────

def grafico_serie_temporal(hitos: list[dict], path: Path):
    hs = hitos_con_serie(hitos)
    fig, axes = plt.subplots(3, 3, figsize=(18, 12))
    fig.suptitle("δ(t) POR NODO — Serie temporal de snapshots", fontsize=14, fontweight="bold", color="#e0e0e0", y=0.98)

    for idx, nodo in enumerate(NODOS):
        ax = axes[idx // 3][idx % 3]
        ax.set_facecolor("#0a0a0a")

        for h in hs:
            serie = h["serie"]
            fechas = [s["fecha"] for s in serie]
            deltas = [s["nodos"][nodo]["delta"] for s in serie]
            color = COLOR_HITOS.get(h["id"], "#888")
            label = LABEL_HITO.get(h["id"], h["id"])
            ax.plot(range(len(serie)), deltas, "o-", color=color, lw=2, markersize=6, label=label, alpha=0.8)

            if len(deltas) >= 2:
                xs = np.arange(len(deltas))
                z = np.polyfit(xs, deltas, 1)
                p = np.poly1d(z)
                ax.plot(xs, p(xs), "--", color=color, lw=1, alpha=0.4)

            for i, d in enumerate(deltas):
                ax.text(i, d + 0.5, f"{d:.1f}", ha="center", fontsize=6, color=color, alpha=0.7)

        ax.set_xticks(range(max(len(h["serie"]) for h in hs)))
        ax.set_xlabel("Snapshot #", fontsize=8)
        ax.set_ylabel("δ (grados)", fontsize=8)
        ax.set_title(nodo, fontsize=12, fontweight="bold", color="#e0e0e0", pad=8)
        ax.grid(True, alpha=0.15, color="#444")
        if idx == 0:
            ax.legend(fontsize=7, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0", loc="upper left")

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 2: Velocidad media por nodo (barras agrupadas por hito) ──

def grafico_velocidad_barras(hitos: list[dict], path: Path):
    hs = hitos_con_serie(hitos)
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.set_facecolor("#0a0a0a")

    x = np.arange(len(NODOS))
    w = 0.12

    for i, h in enumerate(hs):
        vel = h.get("velocidades", {})
        medias = [vel.get(n, {}).get("media", 0) for n in NODOS]
        offset = (i - len(hs) / 2 + 0.5) * w
        color = COLOR_HITOS.get(h["id"], "#888")
        bars = ax.bar(x + offset, medias, w, label=LABEL_HITO.get(h["id"], h["id"]),
                      color=color, alpha=0.85, edgecolor="white", linewidth=0.3)
        for bar, v in zip(bars, medias):
            if abs(v) > 0.3:
                ypos = bar.get_height() + (0.3 if v >= 0 else -0.3)
                va = "bottom" if v >= 0 else "top"
                ax.text(bar.get_x() + bar.get_width() / 2, ypos,
                        f"{v:+.2f}", ha="center", va=va, fontsize=5.5, fontweight="bold", color="#e0e0e0")

    ax.axhline(y=0, color="#666", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(NODOS, fontsize=9)
    ax.set_ylabel("Velocidad media (δ/día)", fontsize=11)
    ax.set_title("VELOCIDAD MEDIA POR NODO — δ/día por hito", fontsize=14, fontweight="bold", color="#e0e0e0", pad=15)
    ax.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")
    ax.grid(True, axis="y", alpha=0.15, color="#444")

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 3: Vector field — aceleración vs velocidad media ─────────

def grafico_vector_field(hitos: list[dict], path: Path):
    hs = hitos_con_serie(hitos)
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("ACELERACIÓN vs VELOCIDAD MEDIA por nodo", fontsize=14, fontweight="bold", color="#e0e0e0", y=0.98)

    for idx, nodo in enumerate(NODOS):
        if idx >= 6:
            break
        ax = axes[idx // 3][idx % 3]
        ax.set_facecolor("#0a0a0a")

        for h in hs:
            vel = h.get("velocidades", {}).get(nodo, {})
            v_media = vel.get("media", 0)
            acel = vel.get("aceleracion", 0) or 0
            color = COLOR_HITOS.get(h["id"], "#888")
            ax.scatter(v_media, acel, c=color, s=80, alpha=0.9, edgecolors="white", linewidth=0.5, zorder=5)
            ax.annotate(LABEL_HITO.get(h["id"], h["id"]).split()[0],
                        (v_media, acel), textcoords="offset points", xytext=(5, 5),
                        fontsize=7, color=color, alpha=0.8)

        ax.axhline(y=0, color="#555", lw=0.8)
        ax.axvline(x=0, color="#555", lw=0.8)
        ax.set_xlabel("Velocidad media (δ/día)", fontsize=9)
        ax.set_ylabel("Aceleración (δ/día²)", fontsize=9)
        ax.set_title(nodo, fontsize=12, fontweight="bold", color="#e0e0e0", pad=8)
        ax.grid(True, alpha=0.15, color="#444")

        # cuadrantes
        ax.axhline(y=0, color="#555", lw=0.5)
        ax.axvline(x=0, color="#555", lw=0.5)

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 4: Velocidad máxima absoluta por nodo ────────────────────

def grafico_velocidad_max(hitos: list[dict], path: Path):
    hs = hitos_con_serie(hitos)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_facecolor("#0a0a0a")

    x = np.arange(len(NODOS))
    w = 0.12

    for i, h in enumerate(hs):
        vel = h.get("velocidades", {})
        max_vals = [abs(vel.get(n, {}).get("max", 0)) for n in NODOS]
        offset = (i - len(hs) / 2 + 0.5) * w
        color = COLOR_HITOS.get(h["id"], "#888")
        bars = ax.bar(x + offset, max_vals, w, label=LABEL_HITO.get(h["id"], h["id"]),
                      color=color, alpha=0.85, edgecolor="white", linewidth=0.3)
        for bar, v in zip(bars, max_vals):
            if v > 1:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        f"{v:.1f}", ha="center", va="bottom", fontsize=5.5, fontweight="bold", color="#e0e0e0")

    ax.set_xticks(x)
    ax.set_xticklabels(NODOS, fontsize=9)
    ax.set_ylabel("|v_max| (δ/día)", fontsize=11)
    ax.set_title("VELOCIDAD MÁXIMA ABSOLUTA POR NODO", fontsize=14, fontweight="bold", color="#e0e0e0", pad=15)
    ax.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")
    ax.grid(True, axis="y", alpha=0.15, color="#444")

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── HTML Report ──────────────────────────────────────────────────────

def generar_html(hitos: list[dict]) -> str:
    hs = hitos_con_serie(hitos)

    section_series = ""
    for h in hs:
        pid = h["id"]
        label = LABEL_HITO.get(pid, pid)
        vel = h.get("velocidades", {})
        rows = ""
        for n in NODOS:
            v = vel.get(n, {})
            if abs(v.get("media", 0)) > 0.3 or abs(v.get("max", 0)) > 1:
                dc = "#ff6b35" if abs(v["media"]) > 1 else "#ffd700" if abs(v["media"]) > 0.5 else "#44ff88"
                dir_arrow = "▲" if v.get("direccion") == "+" else "▼"
                rows += f"<tr><td>{n}</td><td style='color:{dc}'>{v.get('media',0):+.3f}</td><td>{abs(v.get('max',0)):.2f}</td><td>{dir_arrow}</td><td>{v.get('aceleracion','—') or '—'}</td></tr>"
        if not rows:
            continue
        section_series += f"""
        <div class="periodo-card" style="border-left:4px solid {COLOR_HITOS.get(pid, '#888')}">
            <h3>{label}</h3>
            <div class="periodo-meta">{len(h['serie'])} snapshots · {h['serie'][0]['fecha']} → {h['serie'][-1]['fecha']}</div>
            <table>
                <tr><th>Nodo</th><th>v_media (δ/día)</th><th>|v_max|</th><th>Dir</th><th>Acel</th></tr>
                {rows}
            </table>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Velocidad Cultural — Series Temporales</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a0a; color:#e0e0e0; font-family:'Segoe UI',system-ui,sans-serif; padding:30px; }}
  h1 {{ color:#ffd700; font-size:1.6em; margin-bottom:5px; }}
  .sub {{ color:#888; font-size:0.9em; margin-bottom:25px; }}
  .section {{ margin:35px 0 15px; padding-bottom:5px; border-bottom:1px solid #333; color:#ffd700; font-size:1.2em; }}
  img {{ width:100%; max-width:1100px; border-radius:6px; border:1px solid #333; margin:15px 0; display:block; }}
  table {{ border-collapse:collapse; width:100%; font-size:0.85em; margin:12px 0; }}
  th, td {{ border:1px solid #333; padding:6px 10px; text-align:center; }}
  th {{ background:#1a1a1a; color:#aaa; font-weight:600; }}
  .periodo-card {{ background:#141414; border-radius:8px; padding:14px 18px; margin:12px 0; }}
  .periodo-meta {{ color:#888; font-size:0.85em; margin:4px 0 10px; }}
</style>
</head>
<body>
<h1>VELOCIDAD CULTURAL — Series Temporales de Snapshots</h1>
<div class="sub">{len(hs)} hitos con series · {len(NODOS)} nodos culturales</div>

<div class="section">Velocidades por Hito</div>
{section_series}

<div class="section">📈 δ(t) por Nodo — Serie Temporal</div>
<img src="velocidad_serie_temporal.png" alt="Serie temporal δ(t)">

<div class="section">📊 Velocidad Media por Nodo</div>
<img src="velocidad_barras.png" alt="Velocidad media">

<div class="section">🎯 Velocidad Máxima Absoluta</div>
<img src="velocidad_max.png" alt="Velocidad máxima">

<div class="section">🧭 Aceleración vs Velocidad</div>
<img src="velocidad_vector_field.png" alt="Vector field aceleración vs velocidad">

<div class="sub" style="margin-top:30px;text-align:center;color:#555;font-size:0.8em">
  Generado el · Topología Social
</div>
</body>
</html>"""


# ── Generar todo ─────────────────────────────────────────────────────

def generar_todos(salida: Path | None = None) -> list[Path]:
    if salida is None:
        salida = REPORTES_DIR
    salida.mkdir(parents=True, exist_ok=True)

    hitos = cargar_hitos()
    if not hitos:
        print("No hay hitos cargados.")
        return []

    archivos = [
        ("velocidad_serie_temporal.png", grafico_serie_temporal),
        ("velocidad_barras.png", grafico_velocidad_barras),
        ("velocidad_max.png", grafico_velocidad_max),
        ("velocidad_vector_field.png", grafico_vector_field),
    ]

    paths = []
    for name, fn in archivos:
        p = salida / name
        fn(hitos, p)
        paths.append(p)
        print(f"  {name}")

    html = generar_html(hitos)
    (salida / "velocidad.html").write_text(html, encoding="utf-8")
    print(f"  velocidad.html")

    return paths


def main():
    print("Generando gráficos de velocidad cultural...")
    archivos = generar_todos()
    print(f"\n{len(archivos)} gráficos generados en: {REPORTES_DIR}")
    for a in archivos:
        print(f"  {a.name}  ({a.stat().st_size / 1024:.0f} KB)")
    print(f"  velocidad.html")


if __name__ == "__main__":
    main()
