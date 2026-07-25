"""
Gráficos de timeline con estilo plano complejo (e^(2πi / M)).
Anotaciones teóricas + contexto noticioso por nodo.
"""

from __future__ import annotations

import json
import math
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from topologia.math.torus import coherencia_formas, diferencia_angular, forma_cultural_compleja
from topologia.paths import get_reportes_dir
from topologia.web.brechas import resumir_contexto_noticioso

# ── Configuración visual ──────────────────────────────────────────────

plt.rcParams["figure.facecolor"] = "#0a0a0a"
plt.rcParams["axes.facecolor"] = "#0a0a0a"
plt.rcParams["text.color"] = "#e0e0e0"
plt.rcParams["axes.labelcolor"] = "#e0e0e0"
plt.rcParams["xtick.color"] = "#e0e0e0"
plt.rcParams["ytick.color"] = "#e0e0e0"
plt.rcParams["axes.edgecolor"] = "#333"
plt.rcParams["grid.color"] = "#222"

C_Mm = "#00d4ff"
C_Ml = "#c084fc"
C_Ms = "#ff6b35"
C_DELTA = "#ffd700"
C_TENSION = "#ff4444"
C_THETA = "#44ff88"
C_COH = "#44ff88"

NODOS = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]

TRANS = {"m": C_Mm, "l": C_Ml, "s": C_Ms}
TRANS_LABEL = {"m": "M_m · Existencia (Material)", "l": "M_l · Comprensión (Lógico-valórico)", "s": "M_s · Acción (Social)"}
TRANS_LIST = ("m", "l", "s")

REPORTES_DIR = get_reportes_dir()
DESKTOP = Path.home() / "Desktop"


# ── Carga de datos ────────────────────────────────────────────────────

def cargar_timeline() -> list[dict]:
    p = Path(__file__).resolve().parent.parent / "data" / "barrido" / "timeline.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def preparar_formas(data: list[dict]) -> list[dict]:
    estados = []
    for r in data:
        vals = {"m": {}, "l": {}, "s": {}}
        for nid in NODOS:
            nd = r.get(nid, {})
            vals["m"][nid] = nd.get("m", 5.0) / 9.9
            vals["l"][nid] = nd.get("l", 5.0) / 9.9
            vals["s"][nid] = nd.get("s", 5.0) / 9.9
        formas = {}
        for key in TRANS_LIST:
            M = sum(vals[key].values())
            F = forma_cultural_compleja(M)
            formas[key] = {"suma": M, "M": M, "F": F, "ang": float(np.angle(F))}
        estados.append({
            "fecha": r["fecha"],
            "fecha_label": r["fecha"][-5:],
            "era_k": r["era_k"],
            "delta": r["delta"],
            "tension": r["tension"],
            "theta": r["theta_cultura"],
            "coherente": r["coherente"],
            "gap": r["gap"],
            "fragiles": [n for n in NODOS if r.get(n, {}).get("fragil") == "!"],
            "M_m": r["M_m"],
            "M_l": r["M_l"],
            "M_s": r["M_s"],
            "vals": vals,
            "formas": formas,
        })
    return estados


# ── Gráfico 1: Órbita temporal ───────────────────────────────────────

def grafico_orbita_temporal(estados: list[dict], path: Path, contexto: dict | None = None) -> None:
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_facecolor("#0a0a0a")

    ax.add_patch(mpatches.Circle((0, 0), 1, fill=False, color="#333", ls="--", lw=1.5))
    for r in (0.3, 0.6, 0.9):
        ax.add_patch(mpatches.Circle((0, 0), r, fill=False, color="#222", ls="--", lw=0.6))
    ax.axhline(y=0, color="#444", lw=0.8)
    ax.axvline(x=0, color="#444", lw=0.8)

    markers = {"m": "o", "l": "^", "s": "s"}

    for key in TRANS_LIST:
        pts = [e["formas"][key]["F"] for e in estados]
        xs = [p.real for p in pts]
        ys = [p.imag for p in pts]

        ax.plot(xs, ys, color=TRANS[key], lw=1.5, alpha=0.5, marker="", zorder=2)

        for i in range(len(pts) - 1):
            dx = pts[i + 1].real - pts[i].real
            dy = pts[i + 1].imag - pts[i].imag
            ax.arrow(pts[i].real, pts[i].imag, dx * 0.85, dy * 0.85,
                     head_width=0.04, head_length=0.04, fc=TRANS[key], ec=TRANS[key],
                     alpha=0.6, lw=1, zorder=3)

        for i, e in enumerate(estados):
            alpha = 0.3 if i % 2 == 0 else 0.6
            size = 60 if i % 2 == 0 else 100
            ax.scatter(xs[i], ys[i], color=TRANS[key], s=size, zorder=4,
                       edgecolors="white", linewidths=1, marker=markers[key], alpha=alpha)
            if i == len(estados) - 1:
                ax.scatter(xs[i], ys[i], color=TRANS[key], s=200, zorder=5,
                           edgecolors="white", linewidths=2, marker=markers[key])

        last = estados[-1]["formas"][key]
        ax.annotate("", xy=(last["F"].real, last["F"].imag), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color=TRANS[key], lw=3))

    # Anotación teórica
    ax.text(0, -1.35, "Ω_k(t) = e^(2πki / ‖W·M(t)‖)",
            fontsize=9, color="#666", ha="center", style="italic")

    leyenda = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=C_Mm, markersize=10,
                   label="M_m · Lógica de la Existencia (Material)", ls="None"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=C_Ms, markersize=10,
                   label="M_s · Lógica de la Acción (Social)", ls="None"),
        plt.Line2D([0], [0], marker="^", color="w", markerfacecolor=C_Ml, markersize=10,
                   label="M_l · Lógica de la Comprensión (Lógico-valórico)", ls="None"),
    ]
    ax.legend(handles=leyenda, loc="upper left", fontsize=8,
              facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")

    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect("equal")
    ax.set_title("ÓRBITA TEMPORAL — Ω_k(t) en el plano complejo\n"
                 f"{estados[0]['fecha']} → {estados[-1]['fecha']}  ({len(estados)} estados)",
                 fontsize=13, fontweight="bold", color="#e0e0e0", pad=15)
    ax.set_xlabel("Re = Coherencia estructural (escudo de Euler)", fontsize=10)
    ax.set_ylabel("Im = Tensión transformadora (cizallamiento dialéctico)", fontsize=10)
    ax.grid(True, alpha=0.12, color="#444")

    # Callout de contexto noticioso en punto crítico
    if contexto:
        pico = max(estados, key=lambda e: e["delta"])
        ctx = contexto.get("_global", {}).get("resumen", "")
        if ctx:
            ax.text(-1.4, -1.0, f"[N] Pico δ={pico['delta']}° ({pico['fecha_label']}):\n{ctx[:80]}",
                    fontsize=7, color="#ffd700", alpha=0.7)

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 2: Tríada evolutiva ──────────────────────────────────────

def grafico_triada_evolutiva(estados: list[dict], path: Path, contexto: dict | None = None) -> None:
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_facecolor("#0a0a0a")

    ax.add_patch(mpatches.Circle((0, 0), 1, fill=False, color="#333", ls="--", lw=1.5))
    ax.axhline(y=0, color="#444", lw=0.8)
    ax.axvline(x=0, color="#444", lw=0.8)

    cmap = plt.cm.plasma
    n = len(estados)

    for i, e in enumerate(estados):
        pts = {}
        for key in TRANS_LIST:
            F = e["formas"][key]["F"]
            pts[key] = (F.real, F.imag)
        color = cmap(i / max(n - 1, 1))
        alpha = 0.15 + 0.6 * (i / max(n - 1, 1))
        ax.add_patch(plt.Polygon(
            [pts["m"], pts["s"], pts["l"]],
            fill=True, facecolor=color, alpha=alpha * 0.3,
            edgecolor=color, linewidth=1.5 + 1.5 * (i / max(n - 1, 1)),
        ))
        centro = ((pts["m"][0] + pts["s"][0] + pts["l"][0]) / 3,
                  (pts["m"][1] + pts["s"][1] + pts["l"][1]) / 3)
        ax.scatter(centro[0], centro[1], color=color, s=30 + 20 * i, marker="*", zorder=6,
                   alpha=0.5 + 0.5 * (i / max(n - 1, 1)))

    ult = estados[-1]
    for key in TRANS_LIST:
        F = ult["formas"][key]["F"]
        ax.annotate("", xy=(F.real, F.imag), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color=TRANS[key], lw=4))
        ax.scatter(F.real, F.imag, color=TRANS[key], s=200, zorder=5,
                   edgecolors="white", linewidths=2)
        ax.text(F.real + 0.2, F.imag + 0.2,
                f"{key.upper()}\nM={ult['formas'][key]['M']:.2f}\nθ={np.degrees(ult['formas'][key]['ang']):.1f}°",
                color=TRANS[key], fontsize=10, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#0a0a0a",
                          edgecolor=TRANS[key], alpha=0.9))

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, n - 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label("Era k (más reciente → más brillante)", rotation=270, labelpad=20, color="white")
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="white")
    cbar.set_ticks(range(0, n, max(1, n // 5)))
    cbar.set_ticklabels([estados[i]["fecha_label"] for i in range(0, n, max(1, n // 5))])

    ax.text(0, -1.35, "Centro de masa cultural — cuanto más centrado, mayor coherencia estructural",
            fontsize=8, color="#666", ha="center", style="italic")

    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect("equal")
    ax.set_title("TRÍADA EVOLUTIVA — Triángulo M_m–M_s–M_l\n"
                 "Cada era k genera una constelación distinta de las 3 lógicas primarias",
                 fontsize=13, fontweight="bold", color="#e0e0e0", pad=15)
    ax.set_xlabel("Parte Real", fontsize=10)
    ax.set_ylabel("Parte Imaginaria", fontsize=10)
    ax.grid(True, alpha=0.12, color="#444")

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 3: Diagrama de fase ──────────────────────────────────────

def grafico_diagrama_fase(estados: list[dict], path: Path, contexto: dict | None = None) -> None:
    fig, ax = plt.subplots(figsize=(11, 8))
    ax.set_facecolor("#0a0a0a")

    thetas = [e["theta"] for e in estados]
    tensions = [e["tension"] for e in estados]

    eras_vistas = set()
    for i, e in enumerate(estados):
        era = e["era_k"]
        color = plt.cm.viridis(era / 30)
        size = 80 + 40 * (i / max(len(estados) - 1, 1))
        label = f"Era {era}" if era not in eras_vistas else ""
        eras_vistas.add(era)
        ax.scatter(thetas[i], tensions[i], color=color, s=size, zorder=5,
                   edgecolors="white", linewidths=1.5, alpha=0.9, label=label)
        # Etiqueta con fecha y contexto si hay pico
        ctx_text = e["fecha_label"]
        if e["delta"] > 50 and contexto:
            g = contexto.get("_global", {}).get("resumen", "")
            ctx_text = f"{e['fecha_label']}: δ={e['delta']:.0f}°"
        ax.text(thetas[i] + 1.5, tensions[i] + 30, ctx_text, fontsize=7, color="#aaa", ha="center")

    for i in range(len(estados) - 1):
        ax.plot(thetas[i:i + 2], tensions[i:i + 2], color="#555", lw=1, alpha=0.4, zorder=1)

    ax.axhline(y=800, color="#ff8844", ls="--", lw=0.8, alpha=0.5, label="Límite vuelco de fase (800)")
    ax.axvline(x=90, color=C_THETA, ls="--", lw=0.8, alpha=0.5, label="θ = 90°")
    ax.axvline(x=100, color=C_TENSION, ls="--", lw=0.8, alpha=0.5, label="θ = 100°")

    for i in range(len(estados) - 1):
        dx = thetas[i + 1] - thetas[i]
        dy = tensions[i + 1] - tensions[i]
        arrow_len = math.sqrt(dx ** 2 + dy ** 2)
        if arrow_len > 5:
            ax.annotate("", xy=(thetas[i + 1] - dx * 0.1, tensions[i + 1] - dy * 0.1),
                        xytext=(thetas[i + 1] - dx * 0.3, tensions[i + 1] - dy * 0.3),
                        arrowprops=dict(arrowstyle="->", color="#888", lw=1.2, alpha=0.6))

    ax.legend(loc="upper left", fontsize=8, facecolor="#1a1a1a",
              edgecolor="#444", labelcolor="#e0e0e0")
    ax.set_xlabel("θ = 2π / M_l  —  Fase cultural (grados)", fontsize=11)
    ax.set_ylabel("Tensión = Σ(M_m × |Δθ|)  —  Cizallamiento torsional", fontsize=11)
    ax.set_title("DIAGRAMA DE FASE — θ vs Tensión\n"
                 "Cada era k habita una región distinta del espacio de fase",
                 fontsize=13, fontweight="bold", color="#e0e0e0", pad=15)
    ax.grid(True, alpha=0.15, color="#444")

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 4: Mapa de calor ─────────────────────────────────────────

def grafico_nodos_heatmap(estados: list[dict], path: Path, contexto: dict | None = None) -> None:
    fechas = [e["fecha_label"] for e in estados]
    delta_mat = np.zeros((len(NODOS), len(estados)))
    for i, n in enumerate(NODOS):
        for j, e in enumerate(estados):
            delta_mat[i, j] = e["vals"]["m"][n] * 9.9

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_facecolor("#0a0a0a")

    im = ax.imshow(delta_mat, cmap="inferno", aspect="auto", vmin=0, vmax=10)

    ax.set_xticks(range(len(estados)))
    ax.set_xticklabels(fechas, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(NODOS)))
    ax.set_yticklabels(NODOS, fontsize=10)

    for i in range(len(NODOS)):
        for j in range(len(estados)):
            v = delta_mat[i, j]
            color = "white" if v < 5 else "#111"
            val_str = f"{v:.1f}"
            # Anotación de contexto noticioso en celdas críticas
            if v < 1.5 and contexto:
                val_str = f"↓{v:.1f}"
            ax.text(j, i, val_str, ha="center", va="center", fontsize=7, color=color)

    era_colors = plt.cm.viridis([e["era_k"] / 30 for e in estados])
    for j, (e, c) in enumerate(zip(estados, era_colors)):
        ax.plot(j, -0.4, marker="s", color=c, markersize=8, transform=ax.get_xaxis_transform(),
                clip_on=False, zorder=10)

    cbar = fig.colorbar(im, ax=ax, shrink=0.7)
    cbar.set_label("Magnitud (0-10) — frontera asintótica ]0, 1[", rotation=270, labelpad=20, color="white")
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="white")

    ax.set_title("MAPA DE CALOR — ‖W·M(t)‖ por nodo\n"
                 "Valores cercanos a 0 = degradación · cercanos a 10 = saturación",
                 fontsize=13, fontweight="bold", color="#e0e0e0", pad=15)

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 5: Radar polar por era ───────────────────────────────────

def grafico_radar_nodos(estados: list[dict], path: Path, contexto: dict | None = None) -> None:
    eras_agrupadas = {}
    for e in estados:
        eras_agrupadas.setdefault(e["era_k"], []).append(e)

    eras_list = sorted(eras_agrupadas.keys())
    n_eras = len(eras_list)
    cols = min(n_eras, 3)
    rows = math.ceil(n_eras / cols)

    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 6 * rows),
                             subplot_kw=dict(projection="polar"))
    axes = axes.flatten() if n_eras > 1 else [axes]

    N = len(NODOS)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    for idx, era in enumerate(eras_list):
        ax = axes[idx]
        ax.set_facecolor("#0a0a0a")
        grupo = eras_agrupadas[era]
        ultimo = grupo[-1]

        valores_m = [ultimo["vals"]["m"][n] * 9.9 for n in NODOS]
        valores_l = [ultimo["vals"]["l"][n] * 9.9 for n in NODOS]
        valores_s = [ultimo["vals"]["s"][n] * 9.9 for n in NODOS]

        for v, c, lbl in [(valores_m, C_Mm, "M_m"), (valores_l, C_Ml, "M_l"), (valores_s, C_Ms, "M_s")]:
            v += v[:1]
            ax.plot(angles, v, "o-", lw=2, color=c, alpha=0.7, label=lbl)
            ax.fill(angles, v, alpha=0.08, color=c)

        # Anillos asintóticos
        ax.add_patch(plt.Circle((0, 0), 0.5, fill=False, color="#ff4444", ls=":", lw=0.5, alpha=0.3))
        ax.add_patch(plt.Circle((0, 0), 9.5, fill=False, color="#ff4444", ls=":", lw=0.5, alpha=0.3))
        ax.text(0, 0.3, "Frontera ]0[", fontsize=5, color="#ff4444", alpha=0.4, ha="center")
        ax.text(0, 9.3, "Frontera ]1[", fontsize=5, color="#ff4444", alpha=0.4, ha="center")

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(NODOS, fontsize=6)
        ax.set_ylim(0, 10)
        ax.set_title(f"Ω_k(t) — Era {era}  |  {grupo[0]['fecha_label']}–{ultimo['fecha_label']}",
                     fontsize=12, fontweight="bold", color="#e0e0e0", pad=20)
        ax.grid(True, alpha=0.3, color="#444")

        if idx == 0:
            ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1),
                      facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")

    for idx in range(n_eras, len(axes)):
        fig.delaxes(axes[idx])

    fig.suptitle("RADAR DE NODOS — Último estado por era\n"
                 "Anillos punteados: fronteras asintóticas ]0[ degradación, ]1[ saturación",
                 fontsize=13, fontweight="bold", color="#e0e0e0", y=1.02)

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Gráfico 6: Evolución de δ ────────────────────────────────────────

def grafico_delta_evolucion(estados: list[dict], path: Path, contexto: dict | None = None) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_facecolor("#0a0a0a")

    fechas = [e["fecha_label"] for e in estados]
    deltas = [e["delta"] for e in estados]
    cohs = [e["coherente"] for e in estados]

    xs = range(len(fechas))
    ax.plot(xs, deltas, color=C_DELTA, marker="o", lw=2.5, markersize=8, zorder=4)
    ax.fill_between(xs, deltas, alpha=0.1, color=C_DELTA)

    for i, (d, c) in enumerate(zip(deltas, cohs)):
        color = C_COH if c == "OK" else C_TENSION
        ax.scatter(i, d, color=color, s=120, zorder=5, edgecolors="white", linewidths=1.5)
        label = f"{d:.0f}°"
        if d > 50 and contexto:
            ctx = contexto.get("_global", {}).get("resumen", "")
            label = f"{d:.0f}° !!"
        ax.text(i, d + 3, label, ha="center", fontsize=8, fontweight="bold", color=C_DELTA)

    ax.axhline(y=70, color=C_TENSION, ls="--", lw=1, alpha=0.5, label="δ > 70°: Nodo frágil (cizallamiento torsional alto)")
    ax.axhline(y=30, color=C_COH, ls="--", lw=0.8, alpha=0.3, label="δ < 30°: Coherencia estructural estable")

    # Contexto noticioso en picos
    if contexto:
        pico = max(enumerate(deltas), key=lambda x: x[1])
        ctx = contexto.get("_global", {}).get("resumen", "")
        if ctx:
            ax.annotate(f"[N] Pico: {ctx[:100]}", xy=(pico[0], pico[1]),
                        xytext=(pico[0] + 2, pico[1] + 10),
                        fontsize=7, color="#ffd700", alpha=0.8,
                        arrowprops=dict(arrowstyle="->", color="#ffd700", alpha=0.4))

    ax.set_xticks(list(xs))
    ax.set_xticklabels(fechas, fontsize=9)
    ax.set_ylabel("δ (grados) — Divergencia entre lógicas primarias", fontsize=10)
    ax.set_title("EVOLUCIÓN DE δ — Cizallamiento torsional del sistema\n"
                 f"Máx: {max(deltas):.0f}°  ·  Mín: {min(deltas):.0f}°  ·  Actual: {deltas[-1]:.0f}°",
                 fontsize=13, fontweight="bold", color="#e0e0e0", pad=15)
    ax.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")
    ax.set_ylim(0, max(deltas) * 1.4)
    ax.grid(True, alpha=0.15, color="#444")

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── Reporte HTML con interpretación ───────────────────────────────────

def _build_interpretacion(nombre_grafico: str, estados: list[dict], contexto: dict | None) -> str:
    """Genera bloque HTML de interpretación contextual debajo de cada gráfico."""
    if not contexto:
        return ""

    global_ctx = contexto.get("_global", {})
    keywords = global_ctx.get("keywords", [])
    total = global_ctx.get("total_items", 0)
    ultimo = estados[-1]
    pico = max(estados, key=lambda e: e["delta"])
    min_delta = min(estados, key=lambda e: e["delta"])
    kw_str = ", ".join(keywords[:5]) if keywords else ""
    frag_str = ", ".join(ultimo["fragiles"]) if ultimo["fragiles"] else "ninguno"
    coh_str = "coherente" if ultimo["coherente"] == "OK" else "incoherente"
    eras = sorted(set(e["era_k"] for e in estados))
    coh_count = sum(1 for e in estados if e["coherente"] == "OK")

    interpretaciones = {
        "grafico_orbita.png": (
            f"<strong>An&aacute;lisis de la &oacute;rbita:</strong> "
            f"δ actual = {ultimo['delta']:.0f}° ({coh_str}). "
            f"Pico del per&iacute;odo: δ={pico['delta']:.0f}° el {pico['fecha']} "
            f"({'coherente' if pico['coherente']=='OK' else 'incoherente'}). "
            f"M_m={ultimo['M_m']:.1f} &middot; M_l={ultimo['M_l']:.1f} &middot; M_s={ultimo['M_s']:.1f}. "
            f"Nodos fr&aacute;giles: {frag_str}. "
            f"Era k={ultimo['era_k']}. "
            f"{'<br><strong>Temas:</strong> ' + kw_str if kw_str else ''}"
        ),
        "grafico_delta.png": (
            f"<strong>Evoluci&oacute;n de δ:</strong> "
            f"δ mide la divergencia angular entre las 3 l&oacute;gicas. "
            f"δ &lt; 30&deg; = coherente; δ &gt; 70&deg; = nodos fr&aacute;giles. "
            f"<strong>Actual:</strong> δ={ultimo['delta']:.0f}° ({coh_str}). "
            f"M&aacute;ximo: {pico['delta']:.0f}° (d&iacute;a {pico['fecha_label']}). "
            f"M&iacute;nimo: {min_delta['delta']:.0f}° (d&iacute;a {min_delta['fecha_label']}). "
            f"Nodos fr&aacute;giles: {frag_str}. "
            f"θ={ultimo['theta']:.0f}°. Tensión={ultimo['tension']:.0f}. "
            f"{'<br><strong>Temas:</strong> ' + kw_str if kw_str else ''}"
        ),
        "grafico_fase.png": (
            f"<strong>Diagrama de fase:</strong> "
            f"θ={ultimo['theta']:.0f}° &middot; Tensión={ultimo['tension']:.0f}. "
            f"Era k={ultimo['era_k']} ({len(eras)} eras en total). "
            f"Umbral de vuelco: 800. "
            f"{'⚠ Se super&oacute; el umbral' if ultimo['tension'] >= 800 else 'No se alcanz&oacute; el umbral de vuelco'}. "
            f"Estados coherentes: {coh_count}/{len(estados)}. "
            f"{'<br><strong>Temas:</strong> ' + kw_str if kw_str else ''}"
        ),
    }
    base = interpretaciones.get(nombre_grafico, "")
    if base and total:
        base += f"<br><small>({total} items informativos procesados en el per&iacute;odo)</small>"
    return base if base else ""


def generar_informe_html(estados: list[dict], contexto: dict | None = None) -> str:
    total = len(estados)
    rango = f"{estados[0]['fecha']} → {estados[-1]['fecha']}"
    eras = sorted(set(e["era_k"] for e in estados))
    coh_count = sum(1 for e in estados if e["coherente"] == "OK")

    rows_html = ""
    for e in estados:
        gap_str = f"+{e['gap']}h" if e["gap"] else ""
        frag = ", ".join(e["fragiles"])
        coh_class = "coh-ok" if e["coherente"] == "OK" else "coh-no"
        rows_html += f"""
        <tr>
            <td>{e['fecha']}</td>
            <td>{e['era_k']}</td>
            <td style="color:{C_DELTA};font-weight:bold">{e['delta']}</td>
            <td style="color:{C_Mm}">{e['M_m']}</td>
            <td style="color:{C_Ml}">{e['M_l']}</td>
            <td style="color:{C_Ms}">{e['M_s']}</td>
            <td style="color:{C_THETA}">{e['theta']}</td>
            <td style="color:{C_TENSION}">{e['tension']:.0f}</td>
            <td class="{coh_class}">{e['coherente']}</td>
            <td>{gap_str}</td>
            <td style="font-size:0.85em">{frag}</td>
        </tr>"""

    # Bloques de interpretación
    interp_orbita = _build_interpretacion("grafico_orbita.png", estados, contexto)
    interp_delta = _build_interpretacion("grafico_delta.png", estados, contexto)
    interp_fase = _build_interpretacion("grafico_fase.png", estados, contexto)

    interp_orbita_html = f'<div class="interpretacion">{interp_orbita}</div>' if interp_orbita else ""
    interp_delta_html = f'<div class="interpretacion">{interp_delta}</div>' if interp_delta else ""
    interp_fase_html = f'<div class="interpretacion">{interp_fase}</div>' if interp_fase else ""

    ctx_keywords = (contexto or {}).get("_global", {}).get("keywords", [])
    keywords_str = ", ".join(ctx_keywords[:8]) if ctx_keywords else ""
    keywords_section = f"""
    <div class="stats">
      <div class="stat-card"><div class="val" style="color:#ffd700">{keywords_str}</div><div class="lbl">Términos dominantes del período</div></div>
    </div>""" if keywords_str else ""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Timeline Cultural — Topología Social</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a0a; color:#e0e0e0; font-family:'Segoe UI',system-ui,sans-serif; padding:30px; }}
  h1 {{ color:#ffd700; font-size:1.6em; margin-bottom:5px; }}
  .sub {{ color:#888; font-size:0.9em; margin-bottom:25px; }}
  .stats {{ display:flex; gap:15px; flex-wrap:wrap; margin-bottom:30px; }}
  .stat-card {{ background:#141414; border:1px solid #333; border-radius:8px; padding:12px 18px; flex:1; min-width:120px; }}
  .stat-card .val {{ font-size:1.5em; font-weight:bold; }}
  .stat-card .lbl {{ font-size:0.75em; color:#888; }}
  img {{ width:100%; max-width:1100px; border-radius:6px; border:1px solid #333; margin:15px 0; display:block; }}
  .interpretacion {{ background:#141414; border-left:3px solid #ffd700; padding:10px 14px; margin:5px 0 20px; font-size:0.85em; color:#ccc; border-radius:0 6px 6px 0; }}
  table {{ border-collapse:collapse; width:100%; font-size:0.85em; margin:20px 0; }}
  th, td {{ border:1px solid #333; padding:6px 10px; text-align:center; }}
  th {{ background:#1a1a1a; color:#aaa; font-weight:600; }}
  .coh-ok {{ color:#44ff88; }}
  .coh-no {{ color:#ff4444; font-weight:bold; }}
  .section {{ margin:35px 0 15px; padding-bottom:5px; border-bottom:1px solid #333; color:#ffd700; font-size:1.2em; }}
</style>
</head>
<body>
<h1>📊 Timeline Cultural — Análisis Torsional</h1>
<div class="sub">{rango} · {total} estados · {len(eras)} eras</div>

{keywords_section}

<div class="stats">
  <div class="stat-card"><div class="val" style="color:{C_DELTA}">{max(e['delta'] for e in estados):.0f}°</div><div class="lbl">δ máximo (cizallamiento)</div></div>
  <div class="stat-card"><div class="val" style="color:{C_TENSION}">{max(e['tension'] for e in estados):.0f}</div><div class="lbl">Tensión máxima</div></div>
  <div class="stat-card"><div class="val" style="color:#44ff88">{max(eras)}</div><div class="lbl">Eras (vuelcos de fase)</div></div>
  <div class="stat-card"><div class="val" style="color:#44ff88">{coh_count}/{total}</div><div class="lbl">Estados coherentes</div></div>
  <div class="stat-card"><div class="val" style="color:{C_Ml}">{estados[-1]['M_m']}/{estados[-1]['M_l']}/{estados[-1]['M_s']}</div><div class="lbl">M actual (3 lógicas)</div></div>
</div>

<div class="section">🌀 Órbita Temporal — Ω_k(t)</div>
<img src="grafico_orbita.png" alt="Órbita temporal">
{interp_orbita_html}

<div class="section">🔺 Tríada Evolutiva</div>
<img src="grafico_triada.png" alt="Tríada evolutiva">

<div class="section">📈 Evolución de δ</div>
<img src="grafico_delta.png" alt="Delta evolution">
{interp_delta_html}

<div class="section">🌌 Diagrama de Fase</div>
<img src="grafico_fase.png" alt="Diagrama de fase">
{interp_fase_html}

<div class="section">🗺️ Mapa de Calor — ‖W·M(t)‖ por nodo</div>
<img src="grafico_heatmap.png" alt="Heatmap nodos">

<div class="section">📡 Radar por Era — Ω_k(t)</div>
<img src="grafico_radar.png" alt="Radar nodos">

<div class="section">📋 Tabla completa</div>
<table>
  <tr><th>Fecha</th><th>Era</th><th>δ</th><th>M_m</th><th>M_l</th><th>M_s</th><th>θ</th><th>Tensión</th><th>Coh</th><th>Gap</th><th>Frágiles</th></tr>
  {rows_html}
</table>

<div class="sub" style="margin-top:30px;text-align:center;color:#555;font-size:0.8em">
  Generado el {datetime.now().strftime("%Y-%m-%d %H:%M")} · Topología Social
</div>
</body>
</html>"""


# ── Función exportable ────────────────────────────────────────────────

GRAPH_NAMES = [
    "grafico_orbita.png",
    "grafico_triada.png",
    "grafico_delta.png",
    "grafico_fase.png",
    "grafico_heatmap.png",
    "grafico_radar.png",
]

GRAPH_FNS = [
    grafico_orbita_temporal,
    grafico_triada_evolutiva,
    grafico_delta_evolucion,
    grafico_diagrama_fase,
    grafico_nodos_heatmap,
    grafico_radar_nodos,
]


def generar_todos(salida: Path | None = None,
                  items_por_nodo: dict | None = None) -> list[Path]:
    if salida is None:
        salida = REPORTES_DIR
    salida.mkdir(parents=True, exist_ok=True)

    contexto = resumir_contexto_noticioso(items_por_nodo) if items_por_nodo else None

    data = cargar_timeline()
    estados = preparar_formas(data)

    archivos = []
    for name, fn in zip(GRAPH_NAMES, GRAPH_FNS):
        path = salida / name
        fn(estados, path, contexto)
        archivos.append(path)

    html = generar_informe_html(estados, contexto)
    (salida / "timeline.html").write_text(html, encoding="utf-8")

    return archivos


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    archivos = generar_todos()
    print(f"Generados {len(archivos)} gráficos en: {REPORTES_DIR}")
    for a in archivos:
        print(f"  {a.name}")
    print(f"  timeline.html")

    desktop_dir = DESKTOP / "topologia_timeline"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    for a in archivos:
        shutil.copy2(a, desktop_dir / a.name)
    shutil.copy2(REPORTES_DIR / "timeline.html", desktop_dir / "timeline.html")
    print(f"\nCopiado a: {desktop_dir}")


if __name__ == "__main__":
    main()
