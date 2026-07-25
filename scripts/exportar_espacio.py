from __future__ import annotations

import json
import math
from pathlib import Path

import yaml

CONFIG_HITOS = Path(__file__).resolve().parent.parent / "config" / "hitos.yaml"

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from topologia.paths import get_reportes_dir
REPORTES_DIR = get_reportes_dir()

NODOS_COMPLETOS = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]

NODOS_FILTRADOS = {
    "RELIGION": "delta=0 en 6/7 hitos, solo activo en plebiscito_1988 (delta=2.2) — falso positivo en distancias",
}

NODOS = [n for n in NODOS_COMPLETOS if n not in NODOS_FILTRADOS]


def cargar_hitos() -> list[dict]:
    with open(CONFIG_HITOS, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _mls_vector(nodos: dict) -> list[float]:
    vec = []
    for n in NODOS:
        nd = nodos.get(n, {})
        vec.extend([nd.get("m", 5), nd.get("l", 5), nd.get("s", 5)])
    return vec


def _delta_vector(nodos: dict) -> list[float]:
    return [nodos.get(n, {}).get("delta", 0) for n in NODOS]


def _dist_euclidiana(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a)) * math.sqrt(sum((y - mb) ** 2 for y in b))
    return num / den if den else 0


def exportar(hitos: list[dict]) -> dict:
    estados = {}
    for h in hitos:
        pid = h["id"]
        e = h["estado"]
        estados[pid] = {
            "id": pid,
            "descripcion": h.get("descripcion", ""),
            "periodo": h["periodo"],
            "tipo": ("ESPONTANEO" if "estallido" in pid
                     else "EXTERNO" if "pandemia" in pid or "temporal" in pid
                     else "POLITICO"),
            "estado": e,
            "vector_mls": _mls_vector(h["nodos"]),
            "vector_delta": _delta_vector(h["nodos"]),
            "nodos": {n: h["nodos"].get(n, {}) for n in NODOS},
        }

    trayectorias = {}
    for h in hitos:
        serie = h.get("serie", [])
        if not serie:
            continue
        pid = h["id"]
        trayectorias[pid] = []
        for s in serie:
            entry = {
                "fecha": s["fecha"],
                "delta_promedio": s["estado"]["delta_promedio"],
                "M_m": s["estado"]["M_m"],
                "M_l": s["estado"]["M_l"],
                "M_s": s["estado"]["M_s"],
                "vector_mls": _mls_vector(s["nodos"]),
                "vector_delta": _delta_vector(s["nodos"]),
                "nodos": {n: s["nodos"].get(n, {}) for n in NODOS},
            }
            trayectorias[pid].append(entry)

    velocidades = {}
    for h in hitos:
        vel = h.get("velocidades", {})
        if vel:
            velocidades[h["id"]] = {
                n: v for n, v in vel.items()
            }

    pids = [h["id"] for h in hitos]
    dist_matrix = {}
    for i, a in enumerate(pids):
        dist_matrix[a] = {}
        for b in pids:
            va = estados[a]["vector_delta"]
            vb = estados[b]["vector_delta"]
            dist_matrix[a][b] = {
                "euclidiana_delta": round(_dist_euclidiana(va, vb), 4),
                "pearson_delta": round(_pearson(va, vb), 4),
            }

    dist_matrix_mls = {}
    for i, a in enumerate(pids):
        dist_matrix_mls[a] = {}
        for b in pids:
            va = estados[a]["vector_mls"]
            vb = estados[b]["vector_mls"]
            dist_matrix_mls[a][b] = {
                "euclidiana_mls": round(_dist_euclidiana(va, vb), 4),
                "pearson_mls": round(_pearson(va, vb), 4),
            }

    resumen = []
    for h in hitos:
        e = h["estado"]
        resumen.append({
            "id": h["id"],
            "tipo": ("ESPONTANEO" if "estallido" in h["id"]
                     else "EXTERNO" if "pandemia" in h["id"] or "temporal" in h["id"]
                     else "POLITICO"),
            "delta_promedio": e["delta_promedio"],
            "tension_total": e["tension_total"],
            "M_m": e["M_m"],
            "M_l": e["M_l"],
            "M_s": e["M_s"],
            "suma_M": e["M_m"] + e["M_l"] + e["M_s"],
            "theta_cultura": e["theta_cultura"],
            "era_k": e["era_k"],
            "operaciones": e.get("operaciones", []) or [],
        })

    return {
        "metadatos": {
            "nodos": NODOS,
            "nodos_completos": NODOS_COMPLETOS,
            "nodos_filtrados": NODOS_FILTRADOS,
            "dimensiones": ["M_m", "M_l", "M_s"],
            "n_hitos": len(hitos),
            "espacio_dimensional": len(NODOS) * 3,
        },
        "resumen": resumen,
        "estados": estados,
        "trayectorias": trayectorias,
        "velocidades": velocidades,
        "distancias_delta": dist_matrix,
        "distancias_mls": dist_matrix_mls,
    }


def main():
    REPORTES_DIR.mkdir(parents=True, exist_ok=True)
    hitos = cargar_hitos()
    data = exportar(hitos)

    archivos = [
        ("espacio_estados.json", data["estados"]),
        ("trayectorias.json", data["trayectorias"]),
        ("velocidades.json", data["velocidades"]),
        ("distancias.json", {
            "delta": data["distancias_delta"],
            "mls": data["distancias_mls"],
        }),
        ("resumen.json", data["resumen"]),
        ("metadatos.json", data["metadatos"]),
    ]

    for name, content in archivos:
        p = REPORTES_DIR / name
        with open(p, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        kb = p.stat().st_size / 1024
        print(f"  {name}  ({kb:.0f} KB)")

    print(f"\nDataset exportado a {REPORTES_DIR}")
    print(f"  {len(hitos)} hitos, {len(NODOS)} nodos activos (filtrados: {list(NODOS_FILTRADOS.keys())}), {len(NODOS)*3} dimensiones")
    for n, razon in NODOS_FILTRADOS.items():
        print(f"    {n}: {razon}")


if __name__ == "__main__":
    main()
