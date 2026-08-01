"""Modelos visuales de la tromba (R×T3) y el tecelado social.

Salidas en el directorio de reportes:
    tromba_chile_3d.png     — la tromba de Chile: 3 hebras (M, L, S) sobre el eje memoria
    tromba_relacion_3d.png  — dos individuos que se relacionan (tromba conica)
    tecelado_chile.png      — los 27 vertices de contacto + nucleo + arrastre
"""

from __future__ import annotations

import cmath
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from topologia.math.coherence import evaluar_ente_fractal
from topologia.math.unity import diferencia_angular
from topologia.models.schemas import EstadoCultural, TipoEnte

plt.rcParams["figure.facecolor"] = "#0a0a0a"
plt.rcParams["axes.facecolor"] = "#0a0a0a"
plt.rcParams["text.color"] = "#e0e0e0"
plt.rcParams["axes.labelcolor"] = "#e0e0e0"
plt.rcParams["xtick.color"] = "#e0e0e0"
plt.rcParams["ytick.color"] = "#e0e0e0"
plt.rcParams["axes.edgecolor"] = "#333"
plt.rcParams["grid.color"] = "#222"

DATA_DIR = Path.home() / ".local" / "share" / "topologia-social" / "data" / "estados"
SALIDA = Path.home() / ".local" / "share" / "topologia-social" / "data" / "reportes"
SOCIEDAD_DEFAULT = "Chile"

COLOR_CANAL = {"M": "#00d4ff", "L": "#ffd700", "S": "#c084fc"}
LABEL_CANAL = {"M": "Cuantificar (M)", "L": "Valorar (L)", "S": "Mover (S)"}
NUCLEO_COLOR = "#ff6b35"
EFECTIVO_COLOR = "#44ff88"

NODOS = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA", "LENGUAJE",
    "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]


def cargar_estados(sociedad: str = SOCIEDAD_DEFAULT) -> list[EstadoCultural]:
    estados = []
    for path in sorted(DATA_DIR.glob(f"{sociedad}_*.json")):
        estados.append(EstadoCultural.model_validate(json.loads(path.read_text(encoding="utf-8"))))
    return estados


def grafico_tromba_chile(estados: list[EstadoCultural], path: Path):
    t = np.arange(len(estados))
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0a0a0a")
    fig.patch.set_facecolor("#0a0a0a")

    for canal in "MLS":
        magnitudes = [getattr(e, f"m_{canal.lower()}") for e in estados]
        radios = [0.9 + m / 9.9 * 0.9 for m in magnitudes]
        angs = [math.radians(getattr(e, f"theta_{canal.lower()}")) for e in estados]
        xs = [r * math.cos(a) for r, a in zip(radios, angs)]
        ys = [r * math.sin(a) for r, a in zip(radios, angs)]
        ax.plot(xs, ys, t, color=COLOR_CANAL[canal], lw=2.5, label=LABEL_CANAL[canal], alpha=0.9)
        ax.scatter(xs, ys, t, color=COLOR_CANAL[canal], s=28, alpha=0.7)

    ax.set_xlabel("cos θ", color="#e0e0e0")
    ax.set_ylabel("sin θ", color="#e0e0e0")
    ax.set_zlabel("memoria (días)", color="#e0e0e0")
    ax.set_title("TROMBA DE CHILE — tres hebras del UNO sobre el eje memoria", fontsize=13, fontweight="bold", color="#e0e0e0", pad=20)
    ax.xaxis.pane.set_facecolor("#1a1a1a")
    ax.yaxis.pane.set_facecolor("#1a1a1a")
    ax.zaxis.pane.set_facecolor("#1a1a1a")
    ax.tick_params(colors="#888")
    ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Tromba Chile: {len(estados)} cortes apilados en {path.name}")


def grafico_tromba_relacion(path: Path):
    """Dos individuos que se relacionan: el acoplamiento deforma el radio -> tromba conica."""
    t = np.linspace(0, 4 * math.pi, 240)

    # Individuo A: se expande al relacionarse (radio crece), fase avanza.
    rA = 1.1 + 0.35 * np.sin(t / 2)
    thetaA = 0.6 * t

    # Individuo B: es arrastrado por A (fase converge hacia la de A, radio se comprime).
    rB = 1.4 - 0.4 * np.sin(t / 2 + 1.0)
    thetaB = 0.6 * t + 1.6 * np.exp(-t / 5)

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0a0a0a")
    fig.patch.set_facecolor("#0a0a0a")

    ax.plot(rA * np.cos(thetaA), rA * np.sin(thetaA), t, color="#00d4ff", lw=2.5, label="Individuo A (se expande)")
    ax.plot(rB * np.cos(thetaB), rB * np.sin(thetaB), t, color="#ff6b35", lw=2.5, label="Individuo B (arrastrado)")
    ax.plot(np.zeros_like(t), np.zeros_like(t), t, color="#333", lw=1, ls="--", label="eje memoria")

    ax.set_xlabel("x", color="#e0e0e0")
    ax.set_ylabel("y", color="#e0e0e0")
    ax.set_zlabel("memoria (t)", color="#e0e0e0")
    ax.set_title("RELACIÓN DE DOS INDIVIDUOS — la tromba cónica del arrastre", fontsize=13, fontweight="bold", color="#e0e0e0", pad=20)
    ax.xaxis.pane.set_facecolor("#1a1a1a")
    ax.yaxis.pane.set_facecolor("#1a1a1a")
    ax.zaxis.pane.set_facecolor("#1a1a1a")
    ax.tick_params(colors="#888")
    ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Tromba relación: 2 entes, radio deformado por el acoplamiento en {path.name}")


def grafico_tecelado(ente, path: Path):
    fig, ax = plt.subplots(figsize=(11, 11))
    ax.set_facecolor("#0a0a0a")

    # cuerpo unitario (el UNO)
    circ = np.linspace(0, 2 * math.pi, 300)
    ax.plot(np.cos(circ), np.sin(circ), color="#333", lw=1.5)
    ax.text(1.08, 0.02, "u = e^{2πi} = 1", color="#666", fontsize=10)

    # 27 vértices de contacto, por canal
    for canal in "MLS":
        pts = [p for k, p in ente.tecelado.items() if k.endswith(f":{canal}")]
        xs = [p.real for p in pts]
        ys = [p.imag for p in pts]
        ax.scatter(xs, ys, c=COLOR_CANAL[canal], s=130, alpha=0.9,
                   edgecolors="white", linewidth=0.6, zorder=5,
                   label=LABEL_CANAL[canal])

    # núcleo θ*
    nucleo = cmath.exp(1j * math.radians(ente.theta_nucleo))
    ax.scatter([nucleo.real], [nucleo.imag], s=420, c=NUCLEO_COLOR, marker="*",
               edgecolors="white", linewidth=1, zorder=6,
               label=f"núcleo {ente.nucleo} θ*={ente.theta_nucleo:.1f}°")

    # ventana ε = 30° alrededor del núcleo
    eps_rad = math.radians(30.0)
    a0 = cmath.phase(nucleo)
    arco = np.linspace(a0 - eps_rad, a0 + eps_rad, 80)
    ax.plot(np.cos(arco), np.sin(arco), color=NUCLEO_COLOR, lw=2.5, alpha=0.7)
    ax.fill_between(np.cos(arco), np.sin(arco), 0, color=NUCLEO_COLOR, alpha=0.06)

    # vértices efectivos p* y flechas de arrastre
    for k, p in ente.tecelado.items():
        p_ef = ente.tecelado_efectivo[k]
        if abs(p - p_ef) < 1e-9:
            continue
        ax.plot([p.real], [p.imag], color=EFECTIVO_COLOR, marker="x", markersize=7, zorder=7)
        ax.annotate("", xy=(p_ef.real, p_ef.imag), xytext=(p.real, p.imag),
                    arrowprops=dict(arrowstyle="-|>", color=EFECTIVO_COLOR, lw=1.1, alpha=0.55))

    # etiqueta del nodo ECONOMIA:S (el ejemplo: lógica social juzgando lo económico)
    p_eco = ente.tecelado.get("ECONOMIA:S")
    if p_eco is not None:
        ax.annotate(
            f"ECONOMÍA:S\nd = {math.degrees(diferencia_angular(p_eco, nucleo)):.1f}°",
            (p_eco.real, p_eco.imag), xytext=(p_eco.real + 0.25, p_eco.imag + 0.25),
            color="#ffffff", fontsize=9, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#fff", lw=0.8, alpha=0.5),
        )

    ax.axhline(0, color="#222", lw=0.5)
    ax.axvline(0, color="#222", lw=0.5)
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect("equal")
    ax.set_xlabel("Re (e^{iθ})", fontsize=11)
    ax.set_ylabel("Im (e^{iθ})", fontsize=11)
    ax.set_title(
        f"TECELADO DE {ente.nombre} — 27 vértices sobre el UNO\n"
        f"R={ente.densidad_R:.3f}  D(30°)={ente.densidad_D:.3f}  (x verde = vértice efectivo bajo arrastre)",
        fontsize=13, fontweight="bold", color="#e0e0e0", pad=15,
    )
    ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0", loc="upper left")

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Tecelado: 27 vertices, nucleo theta*={ente.theta_nucleo:.1f} grados, R={ente.densidad_R:.3f} en {path.name}")


def generar_todos(sociedad: str = SOCIEDAD_DEFAULT) -> list[Path]:
    """Genera los tres modelos (tromba, relación, tecelado) y retorna las rutas."""
    SALIDA.mkdir(parents=True, exist_ok=True)
    estados = cargar_estados(sociedad)
    if not estados:
        print("Sin archivos de estado")
        return []

    rutas = [
        SALIDA / "tromba_chile_3d.png",
        SALIDA / "tromba_relacion_3d.png",
        SALIDA / "tecelado_chile.png",
    ]

    print("Generando modelos de la tromba y el tecelado...\n")

    grafico_tromba_chile(estados, rutas[0])
    grafico_tromba_relacion(rutas[1])
    grafico_tecelado(
        evaluar_ente_fractal(estados[-1], nombre=estados[-1].sociedad, tipo=TipoEnte.sociedad),
        rutas[2],
    )

    print(f"\nModelos generados en: {SALIDA}")
    return rutas


def main():
    generar_todos()


if __name__ == "__main__":
    main()
