from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

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

REPORTES_DIR = get_reportes_dir()
NODOS = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]

COLOR_TIPO = {
    "ESPONTANEO": "#ff6b35",
    "EXTERNO": "#00d4ff",
    "POLITICO": "#c084fc",
}

LABEL_TIPO = {
    "ESPONTANEO": "Espontaneo",
    "EXTERNO": "Externo",
    "POLITICO": "Politico",
}

COLOR_HITO = {
    "plebiscito_1988": "#aaaaaa",
    "estallido_2019": "#ff6b35",
    "pandemia_ola1_2020": "#00d4ff",
    "pandemia_ola2_2021": "#c084fc",
    "temporal_julio_2026": "#ffd700",
    "plebiscito_2020": "#ff4444",
    "estallido_nocturno_2020": "#44ff88",
}

SALIDA = REPORTES_DIR


def cargar_dataset() -> dict:
    with open(SALIDA / "espacio_estados.json", encoding="utf-8") as f:
        return json.load(f)


def _pca_manual(X: np.ndarray, n_components: int = 2) -> np.ndarray:
    X_centered = X - X.mean(axis=0)
    cov = np.cov(X_centered, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvectors = eigenvectors[:, idx]
    return X_centered @ eigenvectors[:, :n_components], eigenvalues[idx]


def grafico_pca_2d(estados: dict, path: Path):
    pids = list(estados.keys())
    X = np.array([estados[pid]["vector_delta"] for pid in pids])
    tipos = [estados[pid].get("tipo", "EXTERNO") for pid in pids]

    X_pca, ev = _pca_manual(X, n_components=2)
    var_exp = ev[:2] / ev.sum() * 100

    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_facecolor("#0a0a0a")

    for pid, tipo, (x, y) in zip(pids, tipos, X_pca):
        color = COLOR_TIPO.get(tipo, "#888")
        ax.scatter(x, y, c=color, s=200, alpha=0.9, edgecolors="white", linewidth=0.8, zorder=5)
        label = pid.replace("_", " ").title()
        offset_x = 0.3 if x < X_pca[:, 0].mean() else -0.3
        ax.annotate(label, (x, y), textcoords="offset points",
                    xytext=(10 if offset_x > 0 else -10, 8),
                    fontsize=9, color="white", fontweight="bold",
                    ha="left" if offset_x > 0 else "right",
                    alpha=0.9)

    # leyenda
    for tipo, color in COLOR_TIPO.items():
        ax.scatter([], [], c=color, s=80, label=LABEL_TIPO[tipo])
    ax.legend(fontsize=10, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")

    ax.set_xlabel(f"PC1 ({var_exp[0]:.1f}% varianza)", fontsize=11)
    ax.set_ylabel(f"PC2 ({var_exp[1]:.1f}% varianza)", fontsize=11)
    ax.set_title("ESPACIO CULTURAL 2D — PCA sobre vectores δ", fontsize=14, fontweight="bold", color="#e0e0e0", pad=15)
    ax.grid(True, alpha=0.1, color="#444")
    ax.axhline(y=0, color="#333", lw=0.5)
    ax.axvline(x=0, color="#333", lw=0.5)

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  PCA 2D: PC1={var_exp[0]:.1f}%, PC2={var_exp[1]:.1f}%")
    return X_pca, ev


def grafico_pca_3d(estados: dict, path: Path):
    pids = list(estados.keys())
    X = np.array([estados[pid]["vector_mls"] for pid in pids])
    tipos = [estados[pid].get("tipo", "EXTERNO") for pid in pids]

    X_pca, ev = _pca_manual(X, n_components=3)
    var_exp = ev[:3] / ev.sum() * 100

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0a0a0a")
    fig.patch.set_facecolor("#0a0a0a")

    for pid, tipo, (x, y, z) in zip(pids, tipos, X_pca):
        color = COLOR_TIPO.get(tipo, "#888")
        ax.scatter(x, y, z, c=color, s=200, alpha=0.9, edgecolors="white", linewidth=0.5)
        ax.text(x, y, z, pid.replace("_", " ").title(), fontsize=8, color="white")

    ax.set_xlabel(f"PC1 ({var_exp[0]:.1f}%)", fontsize=9, color="#e0e0e0")
    ax.set_ylabel(f"PC2 ({var_exp[1]:.1f}%)", fontsize=9, color="#e0e0e0")
    ax.set_zlabel(f"PC3 ({var_exp[2]:.1f}%)", fontsize=9, color="#e0e0e0")
    ax.set_title("ESPACIO CULTURAL 3D — PCA sobre vectores M (27D)", fontsize=14, fontweight="bold", color="#e0e0e0", pad=20)

    ax.xaxis.pane.set_facecolor("#1a1a1a")
    ax.yaxis.pane.set_facecolor("#1a1a1a")
    ax.zaxis.pane.set_facecolor("#1a1a1a")
    ax.xaxis.pane.set_edgecolor("#333")
    ax.yaxis.pane.set_edgecolor("#333")
    ax.zaxis.pane.set_edgecolor("#333")
    ax.tick_params(colors="#888")

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  PCA 3D: PC1={var_exp[0]:.1f}%, PC2={var_exp[1]:.1f}%, PC3={var_exp[2]:.1f}%")
    return X_pca, ev


def grafico_trayectorias_2d(trayectorias: dict, path: Path):
    pids = list(trayectorias.keys())
    if not pids:
        print("  No hay trayectorias que graficar")
        return

    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_facecolor("#0a0a0a")

    for pid in pids:
        snaps = trayectorias[pid]
        if len(snaps) < 2:
            continue
        X = np.array([s["vector_delta"] for s in snaps])
        X_pca, _ = _pca_manual(X, n_components=2)
        color = COLOR_HITO.get(pid, "#888")
        label = pid.replace("_", " ").title()

        ax.plot(X_pca[:, 0], X_pca[:, 1], "o-", color=color, lw=2.5, markersize=8, label=label, alpha=0.8)
        for i, (x, y) in enumerate(X_pca):
            ax.text(x, y, f"t{i}", fontsize=7, color=color, alpha=0.7,
                    ha="center", va="bottom")

        # flecha de direccion
        dx = X_pca[-1, 0] - X_pca[0, 0]
        dy = X_pca[-1, 1] - X_pca[0, 1]
        ax.arrow(X_pca[0, 0], X_pca[0, 1], dx, dy,
                 head_width=0.3, head_length=0.3, fc=color, ec=color, alpha=0.4, lw=1)

    ax.set_xlabel("PC1", fontsize=11)
    ax.set_ylabel("PC2", fontsize=11)
    ax.set_title("TRAYECTORIAS CULTURALES — Serie de snapshots en espacio PCA", fontsize=14, fontweight="bold", color="#e0e0e0", pad=15)
    ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")
    ax.grid(True, alpha=0.1, color="#444")
    ax.axhline(y=0, color="#333", lw=0.5)
    ax.axvline(x=0, color="#333", lw=0.5)

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Trayectorias: {len(pids)} hitos con series")


def grafico_peso_componentes(ev: np.ndarray, path: Path, label: str = ""):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_facecolor("#0a0a0a")

    n = min(len(ev), 9)
    var_exp = ev[:n] / ev.sum() * 100
    cumsum = np.cumsum(var_exp)

    ax.bar(range(n), var_exp, color="#ffd700", alpha=0.85, edgecolor="white", linewidth=0.5, width=0.6)
    ax.plot(range(n), cumsum, "o-", color="#00d4ff", lw=2, markersize=6, label="Acumulado")

    for i, (v, c) in enumerate(zip(var_exp, cumsum)):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=8, color="#e0e0e0")
        if i == n - 1:
            ax.text(i, c - 8, f"{c:.1f}%", ha="center", fontsize=8, color="#00d4ff", fontweight="bold")

    ax.set_xticks(range(n))
    ax.set_xticklabels([f"PC{i+1}" for i in range(n)], fontsize=9)
    ax.set_ylabel("Varianza explicada (%)", fontsize=11)
    ax.set_title(f"COMPONENTES PRINCIPALES {label}", fontsize=14, fontweight="bold", color="#e0e0e0", pad=15)
    ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#444", labelcolor="#e0e0e0")
    ax.grid(True, axis="y", alpha=0.15, color="#444")

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


def grafico_matriz_distancia(estados: dict, path: Path):
    pids = list(estados.keys())
    n = len(pids)
    matrix = np.zeros((n, n))
    for i, a in enumerate(pids):
        for j, b in enumerate(pids):
            va = estados[a]["vector_delta"]
            vb = estados[b]["vector_delta"]
            matrix[i, j] = math.sqrt(sum((x - y) ** 2 for x, y in zip(va, vb)))

    fig, ax = plt.subplots(figsize=(9, 8))
    ax.set_facecolor("#0a0a0a")

    im = ax.imshow(matrix, cmap="inferno", aspect="auto")

    labels = [p.replace("_", " ").title() for p in pids]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, fontsize=8, rotation=45, ha="right")
    ax.set_yticklabels(labels, fontsize=8)

    for i in range(n):
        for j in range(n):
            v = matrix[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                    fontsize=7, fontweight="bold",
                    color="white" if v < matrix.max() * 0.6 else "#111")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Distancia Euclidiana (δ)", rotation=270, labelpad=20, color="white")
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="white")

    ax.set_title("MATRIZ DE DISTANCIAS — δ entre hitos", fontsize=14, fontweight="bold", color="#e0e0e0", pad=15)

    fig.tight_layout()
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    estados = cargar_dataset()

    print("Generando embeddings del espacio cultural...\n")

    # PCA 2D sobre delta
    X_pca_delta, ev_delta = grafico_pca_2d(estados, SALIDA / "embedding_pca_2d_delta.png")
    grafico_peso_componentes(ev_delta, SALIDA / "embedding_varianza_delta.png", label="(vectores δ)")

    # PCA 3D sobre MLS (27D)
    pids = list(estados.keys())
    X_mls = np.array([estados[pid]["vector_mls"] for pid in pids])
    grafico_pca_3d(estados, SALIDA / "embedding_pca_3d_mls.png")
    _, ev_mls = _pca_manual(X_mls, n_components=min(len(pids), len(NODOS) * 3))
    grafico_peso_componentes(ev_mls, SALIDA / "embedding_varianza_mls.png", label="(vectores M 27D)")

    # Matriz de distancias
    grafico_matriz_distancia(estados, SALIDA / "embedding_matriz_distancia.png")

    # Trayectorias (PCA sobre snapshots)
    with open(SALIDA / "trayectorias.json", encoding="utf-8") as f:
        trayectorias = json.load(f)
    grafico_trayectorias_2d(trayectorias, SALIDA / "embedding_trayectorias_2d.png")

    print(f"\nEmbeddings generados en: {SALIDA}")


if __name__ == "__main__":
    main()
