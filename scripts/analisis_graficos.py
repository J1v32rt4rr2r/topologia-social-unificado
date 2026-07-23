from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from topologia.math.torus import (
    coherencia_formas,
    diferencia_angular,
    forma_cultural_compleja,
)
from topologia.paths import get_reportes_dir
from topologia.storage.store import FileStore
from topologia.web.brechas import resumir_contexto_noticioso

NODOS_IDS = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]

plt.rcParams["figure.facecolor"] = "#0a0a0a"
plt.rcParams["axes.facecolor"] = "#0a0a0a"
plt.rcParams["text.color"] = "#e0e0e0"
plt.rcParams["axes.labelcolor"] = "#e0e0e0"
plt.rcParams["xtick.color"] = "#e0e0e0"
plt.rcParams["ytick.color"] = "#e0e0e0"

COLORES = {"m": "#00d4ff", "l": "#c084fc", "s": "#ff6b35"}
ETIQUETAS = {
    "m": "M_m (Material)",
    "l": "M_l (L\u00f3gico-val\u00f3rico)",
    "s": "M_s (Social)",
}
TRANSVERSALES = ("m", "l", "s")


def cargar_datos(
    sociedad: str = "Chile",
    fecha_antes: str | None = None,
    fecha_despues: str | None = None,
) -> tuple[dict, dict, str, str]:
    store = FileStore()
    fechas = store.listar_estados(sociedad)

    if fecha_antes is None:
        fecha_antes = fechas[0]
    if fecha_despues is None:
        fecha_despues = fechas[-1]

    e_antes = store.cargar_estado(sociedad, fecha_antes)
    e_despues = store.cargar_estado(sociedad, fecha_despues)
    if not e_antes or not e_despues:
        raise ValueError("No se pudieron cargar los estados")

    def extraer(estado):
        vals = {"m": {}, "l": {}, "s": {}}
        compat = {"CONTINUIDAD": "SEXUALIDAD"}
        for n in estado.nodos:
            nid = compat.get(n.nodo_id, n.nodo_id)
            vals["m"][nid] = n.dimension_m / 9.9
            vals["l"][nid] = n.dimension_l / 9.9
            vals["s"][nid] = n.dimension_s / 9.9
        return vals

    return extraer(e_antes), extraer(e_despues), fecha_antes, fecha_despues


def calcular_formas(vals: dict) -> dict:
    formas = {}
    for key in TRANSVERSALES:
        M = sum(vals[key].values())
        F = forma_cultural_compleja(M)
        formas[key] = {"suma": M, "M": M, "F": F, "ang": float(np.angle(F))}
    return formas


def grafico_plano_complejo(f_antes: dict, f_despues: dict, fechas: tuple[str, str], salida: Path, contexto: dict | None = None):
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle(
        "FORMA CULTURAL: e^(2\u03c0i / M)",
        fontsize=16, fontweight="bold", color="#e0e0e0", y=0.98,
    )

    for ax, datos, titulo in [
        (axes[0], f_antes, fechas[0]),
        (axes[1], f_despues, fechas[1]),
    ]:
        ax.set_facecolor("#0a0a0a")
        ax.add_patch(mpatches.Circle((0, 0), 1, fill=False, color="#333333", ls="--", lw=1.5))
        ax.axhline(y=0, color="#444444", lw=0.8)
        ax.axvline(x=0, color="#444444", lw=0.8)

        for key in TRANSVERSALES:
            F = datos[key]["F"]
            ang = datos[key]["ang"]
            ax.annotate(
                "", xy=(F.real, F.imag), xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color=COLORES[key], lw=3),
            )
            ax.scatter(F.real, F.imag, color=COLORES[key], s=150, zorder=5,
                       edgecolors="white", linewidths=2)
            offset = 0.15
            ax.text(
                F.real + offset, F.imag + offset,
                f"{ETIQUETAS[key]}\nM={datos[key]['M']:.2f}\n\u03b8={np.degrees(ang):.1f}\u00b0",
                color=COLORES[key], fontsize=10, fontweight="bold",
            )
            ax.add_patch(mpatches.Arc(
                (0, 0), 0.4, 0.4, angle=0,
                theta1=0, theta2=np.degrees(ang),
                color=COLORES[key], lw=2, alpha=0.6,
            ))

        context_global = (contexto or {}).get("_global", {})
        keywords = context_global.get("keywords", [])
        if keywords:
            ax.text(1.3, -1.2, "\n".join(keywords[:4]),
                    fontsize=7, color="#ffd700", alpha=0.6, ha="right",
                    bbox=dict(boxstyle="round", facecolor="#111", edgecolor="#ffd700", alpha=0.5))
            ax.annotate("Términos clave del período", xy=(0.9, -1.1),
                        fontsize=6, color="#666", style="italic")

        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.3)
        ax.set_aspect("equal")
        ax.set_title(titulo, fontsize=14, fontweight="bold", color="#e0e0e0", pad=20)
        ax.set_xlabel("Parte Real (coherencia estructural)", fontsize=11)
        ax.set_ylabel("Parte Imaginaria (tensi\u00f3n transformadora)", fontsize=11)
        ax.grid(True, alpha=0.2, color="#444444")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(str(salida / "grafico_plano_complejo.png"), dpi=150,
                bbox_inches="tight", facecolor="#0a0a0a", edgecolor="none")
    plt.close()


def grafico_rotacion_angular(f_antes: dict, f_despues: dict, fechas: tuple[str, str], salida: Path, contexto: dict | None = None):
    fig, ax = plt.subplots(figsize=(14, 14))
    ax.set_facecolor("#0a0a0a")

    ax.add_patch(mpatches.Circle((0, 0), 1, fill=False, color="#333333", lw=2))
    for r in (0.3, 0.6, 0.9):
        ax.add_patch(mpatches.Circle((0, 0), r, fill=False, color="#222222", ls="--", lw=0.8))
    ax.axhline(y=0, color="#444444", lw=1)
    ax.axvline(x=0, color="#444444", lw=1)

    markers = {"m": "o", "l": "^", "s": "s"}
    radios = {"m": 1.4, "l": 1.8, "s": 1.6}

    for key in TRANSVERSALES:
        Fa = f_antes[key]
        Fd = f_despues[key]
        delta = diferencia_angular(Fa["F"], Fd["F"])

        ax.scatter(Fa["F"].real, Fa["F"].imag, color=COLORES[key], s=200, zorder=5,
                   edgecolors="white", linewidths=2, marker=markers[key], alpha=0.6)
        ax.scatter(Fd["F"].real, Fd["F"].imag, color=COLORES[key], s=300, zorder=5,
                   edgecolors="white", linewidths=3, marker=markers[key])

        r = radios[key]
        ax.add_patch(mpatches.Arc(
            (0, 0), r, r, angle=0,
            theta1=np.degrees(Fa["ang"]), theta2=np.degrees(Fd["ang"]),
            color=COLORES[key], lw=4, alpha=0.8,
        ))

        mid = (Fa["ang"] + Fd["ang"]) / 2
        if abs(Fd["ang"] - Fa["ang"]) > np.pi:
            mid += np.pi
        ax.annotate(
            "", xy=(r / 2 * np.cos(Fd["ang"] + 0.05), r / 2 * np.sin(Fd["ang"] + 0.05)),
            xytext=(r / 2 * np.cos(mid), r / 2 * np.sin(mid)),
            arrowprops=dict(arrowstyle="->", color=COLORES[key], lw=3),
        )

        ax.text(
            Fa["F"].real - 0.25, Fa["F"].imag + 0.15,
            f"{key.upper()} {fechas[0]}\nM={Fa['M']:.2f}",
            color=COLORES[key], fontsize=9, alpha=0.6, ha="center",
        )
        ax.text(
            Fd["F"].real - 0.4, Fd["F"].imag - 0.25,
            f"{key.upper()} {fechas[1]}\nM\u2032={Fd['M']:.2f}\n\u0394\u03b8={np.degrees(delta):.1f}\u00b0",
            color=COLORES[key], fontsize=11, fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#0a0a0a",
                      edgecolor=COLORES[key], alpha=0.9),
        )

    diffs = [diferencia_angular(f_antes[k]["F"], f_despues[k]["F"]) for k in TRANSVERSALES]
    delta_prom = np.degrees(sum(diffs) / 3)
    diag = f"DIAGN\u00d3STICO\n\u0394\u03b8 promedio = {delta_prom:.1f}\u00b0"
    if delta_prom > 90:
        diag += "\n> \u03c0/2 — Rotaci\u00f3n significativa"
    ax.text(
        1.4, -1.4, diag,
        fontsize=11, color="#ff4444", fontweight="bold", ha="right",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1a1a",
                  edgecolor="#ff4444", alpha=0.9),
    )

    context_global = (contexto or {}).get("_global", {})
    keywords = context_global.get("keywords", [])
    if keywords:
        ax.text(1.3, -1.0, "\n".join(keywords[:4]),
                fontsize=7, color="#ffd700", alpha=0.6, ha="right",
                bbox=dict(boxstyle="round", facecolor="#111", edgecolor="#ffd700", alpha=0.5))

    legend_elements = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORES["m"],
                   markersize=10, label="M_m (Material)", ls="None"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=COLORES["s"],
                   markersize=10, label="M_s (Social)", ls="None"),
        plt.Line2D([0], [0], marker="^", color="w", markerfacecolor=COLORES["l"],
                   markersize=10, label="M_l (L\u00f3gico-val\u00f3rico)", ls="None"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="gray",
                   markersize=8, label=fechas[0], ls="None", alpha=0.5),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="white",
                   markersize=12, label=fechas[1], ls="None"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=10,
              facecolor="#1a1a1a", edgecolor="#444444", labelcolor="#e0e0e0")

    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect("equal")
    ax.set_title(
        f"ROTACI\u00d3N ANGULAR CULTURAL\ne^(2\u03c0i/M)  |  {fechas[0]} \u2192 {fechas[1]}",
        fontsize=16, fontweight="bold", color="#e0e0e0", pad=20,
    )
    ax.set_xlabel("Parte Real (coherencia estructural)", fontsize=12)
    ax.set_ylabel("Parte Imaginaria (tensi\u00f3n transformadora)", fontsize=12)
    ax.grid(True, alpha=0.15, color="#444444")

    plt.tight_layout()
    plt.savefig(str(salida / "grafico_rotacion_angular.png"), dpi=150,
                bbox_inches="tight", facecolor="#0a0a0a", edgecolor="none")
    plt.close()


def grafico_triangulo_coherencia(f_antes: dict, f_despues: dict, fechas: tuple[str, str], salida: Path, contexto: dict | None = None):
    fig, axes = plt.subplots(1, 2, figsize=(18, 9))
    fig.suptitle(
        "TRI\u00c1NGULO DE COHERENCIA CULTURAL  |  e^(2\u03c0i / M)",
        fontsize=16, fontweight="bold", color="#e0e0e0", y=0.98,
    )

    context_global = (contexto or {}).get("_global", {})
    keywords = context_global.get("keywords", [])

    for ax, datos, titulo, es_despues in [
        (axes[0], f_antes, fechas[0], False),
        (axes[1], f_despues, fechas[1], True),
    ]:
        ax.set_facecolor("#0a0a0a")
        ax.add_patch(mpatches.Circle((0, 0), 1, fill=False, color="#333333", ls="--", lw=2))
        ax.axhline(y=0, color="#444444", lw=1)
        ax.axvline(x=0, color="#444444", lw=1)

        pts = {}
        for key in TRANSVERSALES:
            F = datos[key]["F"]
            ang = datos[key]["ang"]
            ax.annotate(
                "", xy=(F.real, F.imag), xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color=COLORES[key], lw=4),
            )
            ax.scatter(F.real, F.imag, color=COLORES[key], s=200, zorder=5,
                       edgecolors="white", linewidths=2)
            ax.add_patch(mpatches.Arc(
                (0, 0), 0.5, 0.5, angle=0, theta1=0, theta2=np.degrees(ang),
                color=COLORES[key], lw=2, alpha=0.7,
            ))
            ax.text(
                F.real + 0.2, F.imag + 0.2,
                f"{key.upper()}\nM={datos[key]['M']:.2f}\n\u03b8={np.degrees(ang):.1f}\u00b0",
                color=COLORES[key], fontsize=11, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#0a0a0a",
                          edgecolor=COLORES[key], alpha=0.9),
            )
            pts[key] = (F.real, F.imag)

        color_tri = "#ff4444" if es_despues else "white"
        alpha_tri = 0.15 if es_despues else 0.08
        lw_tri = 3 if es_despues else 2
        ax.add_patch(plt.Polygon(
            [pts["m"], pts["s"], pts["l"]],
            fill=True, facecolor=color_tri, alpha=alpha_tri,
            edgecolor=color_tri, linewidth=lw_tri,
        ))

        cent = (
            (pts["m"][0] + pts["s"][0] + pts["l"][0]) / 3,
            (pts["m"][1] + pts["s"][1] + pts["l"][1]) / 3,
        )
        ax.scatter(cent[0], cent[1], color=color_tri, s=100, marker="*", zorder=6)
        ax.text(cent[0] + 0.1, cent[1] - 0.15, "Centroide", color=color_tri, fontsize=9)

        area = 0.5 * abs(
            (pts["s"][0] - pts["m"][0]) * (pts["l"][1] - pts["m"][1])
            - (pts["l"][0] - pts["m"][0]) * (pts["s"][1] - pts["m"][1])
        )

        coh = coherencia_formas([datos[k]["F"] for k in TRANSVERSALES])
        ax.text(
            -1.2, -1.2,
            f"\u00c1rea: {area:.3f}\nCoherencia: {np.degrees(coh):.1f}\u00b0",
            color=color_tri, fontsize=10, fontweight="bold",
        )

        if keywords and es_despues:
            ax.text(1.1, -1.1, "\n".join(keywords[:4]),
                    fontsize=7, color="#ffd700", alpha=0.6, ha="right",
                    bbox=dict(boxstyle="round", facecolor="#111", edgecolor="#ffd700", alpha=0.5))

        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.3)
        ax.set_aspect("equal")
        ax.set_title(titulo, fontsize=14, fontweight="bold", color="#e0e0e0", pad=15)
        ax.set_xlabel("Parte Real", fontsize=11)
        ax.set_ylabel("Parte Imaginaria", fontsize=11)
        ax.grid(True, alpha=0.15, color="#444444")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(str(salida / "grafico_triangulo_coherencia.png"), dpi=150,
                bbox_inches="tight", facecolor="#0a0a0a", edgecolor="none")
    plt.close()


def grafico_radar(antes_vals: dict, despues_vals: dict, fechas: tuple[str, str], salida: Path, contexto: dict | None = None):
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), subplot_kw=dict(projection="polar"))
    fig.suptitle(
        "RADAR DE NODOS CULTURALES  |  Chile 2026",
        fontsize=16, fontweight="bold", color="#e0e0e0", y=0.98,
    )

    N = len(NODOS_IDS)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    for idx, key in enumerate(TRANSVERSALES):
        ax = axes[idx]
        ax.set_facecolor("#0a0a0a")

        antes = [antes_vals[key][n] for n in NODOS_IDS]
        despues = [despues_vals[key][n] for n in NODOS_IDS]
        antes += antes[:1]
        despues += despues[:1]

        ax.plot(angles, antes, "o-", lw=2, color=COLORES[key], alpha=0.5, label=fechas[0])
        ax.fill(angles, antes, alpha=0.1, color=COLORES[key])
        ax.plot(angles, despues, "o-", lw=3, color=COLORES[key], label=fechas[1])
        ax.fill(angles, despues, alpha=0.25, color=COLORES[key])

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(NODOS_IDS, fontsize=7)
        ax.set_ylim(0, 1)
        ax.set_title(ETIQUETAS[key], fontsize=14, fontweight="bold",
                     color=COLORES[key], pad=20)
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1),
                  facecolor="#1a1a1a", edgecolor="#444444", labelcolor="#e0e0e0")
        ax.grid(True, alpha=0.3, color="#444444")

    context_global = (contexto or {}).get("_global", {})
    keywords = context_global.get("keywords", [])
    if keywords:
        fig.text(0.02, 0.02, "Términos: " + ", ".join(keywords[:5]),
                 fontsize=8, color="#ffd700", alpha=0.6)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(str(salida / "grafico_radar_nodos.png"), dpi=150,
                bbox_inches="tight", facecolor="#0a0a0a", edgecolor="none")
    plt.close()


def grafico_mapa_calor(antes_vals: dict, despues_vals: dict, fechas: tuple[str, str], salida: Path, contexto: dict | None = None):
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_facecolor("#0a0a0a")

    heatmap_data = np.zeros((9, 9))
    transversales = [("m", 0), ("s", 3), ("l", 6)]

    for i, nodo in enumerate(NODOS_IDS):
        for key, offset in transversales:
            v_ant = antes_vals[key][nodo]
            v_desp = despues_vals[key][nodo]
            heatmap_data[i, offset] = v_ant
            heatmap_data[i, offset + 1] = v_desp
            heatmap_data[i, offset + 2] = v_desp - v_ant

    im = ax.imshow(heatmap_data, cmap="RdYlGn_r", aspect="auto", vmin=-0.5, vmax=0.5)

    ax.set_xticks(range(9))
    ax.set_xticklabels([
        "M_m\nAntes", "M_m\nDespu\u00e9s", "M_m\n\u0394",
        "M_s\nAntes", "M_s\nDespu\u00e9s", "M_s\n\u0394",
        "M_l\nAntes", "M_l\nDespu\u00e9s", "M_l\n\u0394",
    ], fontsize=9)
    ax.set_yticks(range(9))
    ax.set_yticklabels(NODOS_IDS, fontsize=10)

    for i in range(9):
        for j in range(9):
            ax.text(
                j, i, f"{heatmap_data[i, j]:.1f}",
                ha="center", va="center",
                color="white" if abs(heatmap_data[i, j]) > 0.3 else "black",
                fontsize=9, fontweight="bold",
            )

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Valoraci\u00f3n normalizada (/9.9)", rotation=270, labelpad=20, color="white")
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="white")

    context_global = (contexto or {}).get("_global", {})
    keywords = context_global.get("keywords", [])
    if keywords:
        ax.text(10.3, -0.5, "Términos: " + ", ".join(keywords[:4]),
                fontsize=8, color="#ffd700", alpha=0.6, transform=ax.get_xaxis_transform())

    ax.set_title(
        f"MAPA DE CALOR: VARIACI\u00d3N NODAL POR TRANSVERSAL\n"
        f"{fechas[0]} \u2192 {fechas[1]}",
        fontsize=16, fontweight="bold", color="#e0e0e0", pad=20,
    )

    plt.tight_layout()
    plt.savefig(str(salida / "grafico_mapa_calor_nodos.png"), dpi=150,
                bbox_inches="tight", facecolor="#0a0a0a", edgecolor="none")
    plt.close()


def calcular_deltas_theta(sociedad: str = "Chile") -> dict | None:
    """Calcula Δθ para cada dimensión entre el último y penúltimo estado."""
    try:
        antes_vals, despues_vals, f_antes, f_despues = cargar_datos(sociedad)
        f_a = calcular_formas(antes_vals)
        f_d = calcular_formas(despues_vals)
        deltas = {}
        for key in TRANSVERSALES:
            delta = diferencia_angular(f_a[key]["F"], f_d[key]["F"])
            deltas[key] = round(np.degrees(delta), 1)
        return {
            "deltas_theta": deltas,
            "f_a": {k: {"M": v["M"], "theta": np.degrees(v["ang"])} for k, v in f_a.items()},
            "f_d": {k: {"M": v["M"], "theta": np.degrees(v["ang"])} for k, v in f_d.items()},
        }
    except Exception:
        return None


def generar_todos(
    sociedad: str = "Chile",
    fecha_antes: str | None = None,
    fecha_despues: str | None = None,
    salida: Path | None = None,
    items_por_nodo: dict | None = None,
) -> list[Path]:
    if salida is None:
        salida = get_reportes_dir()
    salida.mkdir(parents=True, exist_ok=True)

    contexto = resumir_contexto_noticioso(items_por_nodo) if items_por_nodo else None

    antes_vals, despues_vals, f_antes, f_despues = cargar_datos(sociedad, fecha_antes, fecha_despues)
    fechas = (f_antes, f_despues)

    f_a = calcular_formas(antes_vals)
    f_d = calcular_formas(despues_vals)

    for key in TRANSVERSALES:
        a = f_a[key]
        d = f_d[key]
        delta = diferencia_angular(a["F"], d["F"])
        print(f"  {key.upper()}: M={a['M']:.3f} \u2192 M\u2032={d['M']:.3f}  "
              f"\u03a3={a['suma']:.2f} \u2192 {d['suma']:.2f}  "
              f"\u0394\u03b8={np.degrees(delta):.1f}\u00b0")

    archivos = [
        salida / "grafico_plano_complejo.png",
        salida / "grafico_rotacion_angular.png",
        salida / "grafico_triangulo_coherencia.png",
        salida / "grafico_radar_nodos.png",
        salida / "grafico_mapa_calor_nodos.png",
    ]

    for a in archivos:
        a.unlink(missing_ok=True)

    grafico_plano_complejo(f_a, f_d, fechas, salida, contexto)
    grafico_rotacion_angular(f_a, f_d, fechas, salida, contexto)
    grafico_triangulo_coherencia(f_a, f_d, fechas, salida, contexto)
    grafico_radar(antes_vals, despues_vals, fechas, salida, contexto)
    grafico_mapa_calor(antes_vals, despues_vals, fechas, salida, contexto)

    return archivos


def main():
    parser = argparse.ArgumentParser(
        description="Genera 5 gr\u00e1ficos de an\u00e1lisis cultural (e^(2\u03c0i/m))",
    )
    parser.add_argument(
        "--sociedad", default="Chile",
        help="Sociedad a analizar (default: Chile)",
    )
    parser.add_argument(
        "--antes", default=None,
        help="Fecha inicial (YYYY-MM-DD). Default: primer estado disponible",
    )
    parser.add_argument(
        "--despues", default=None,
        help="Fecha final (YYYY-MM-DD). Default: \u00faltimo estado disponible",
    )
    parser.add_argument(
        "--open", "-o", action="store_true",
        help="Abrir los gr\u00e1ficos al generarlos",
    )
    parser.add_argument(
        "--salida", default=None,
        help="Directorio de salida (default: reportes del proyecto)",
    )
    args = parser.parse_args()

    salida = Path(args.salida) if args.salida else get_reportes_dir()

    print(f"Cargando datos: {args.sociedad}  |  antes={args.antes or 'auto'}  despues={args.despues or 'auto'}")
    archivos = generar_todos(args.sociedad, args.antes, args.despues, salida)

    print(f"\nGenerados {len(archivos)} gr\u00e1ficos en: {salida}")
    for a in archivos:
        print(f"  {a.name}  ({a.stat().st_size / 1024:.0f} KB)")

    if args.open:
        for a in archivos:
            os.startfile(str(a))


if __name__ == "__main__":
    main()
