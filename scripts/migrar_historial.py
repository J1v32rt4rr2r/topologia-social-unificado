"""Migra historial.json legacy al nuevo formato EstadoCultural con nodos estimados."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from topologia.math.torus import calcular_angulos, calcular_delta
from topologia.models.schemas import EstadoCultural, EvaluacionNodo
from topologia.storage.store import FileStore

NODOS_CULTURALES = [
    "ECONOMIA", "TRABAJO", "CONTINUIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]


def estimar_nodos_desde_M(M_m, M_l, M_s, template_nodos):
    """Estima valores por nodo escalando desde el template real y el M target."""
    if not template_nodos:
        return []

    # Calcular M actual del template
    t_m = sum(n.dimension_m for n in template_nodos) / len(template_nodos)
    t_l = sum(n.dimension_l for n in template_nodos) / len(template_nodos)
    t_s = sum(n.dimension_s for n in template_nodos) / len(template_nodos)

    # Factores de escala
    f_m = M_m / t_m if t_m > 0 else 1.0
    f_l = M_l / t_l if t_l > 0 else 1.0
    f_s = M_s / t_s if t_s > 0 else 1.0

    estimados = []
    for n in template_nodos:
        estimados.append(EvaluacionNodo(
            nodo_id=n.nodo_id,
            nodo_nombre=n.nodo_nombre,
            dimension_m=round(min(max(n.dimension_m * f_m, 0.1), 9.9), 1),
            dimension_l=round(min(max(n.dimension_l * f_l, 0.1), 9.9), 1),
            dimension_s=round(min(max(n.dimension_s * f_s, 0.1), 9.9), 1),
            justificacion_m="(dato historico reconstruido)",
            justificacion_l="(dato historico reconstruido)",
            justificacion_s="(dato historico reconstruido)",
        ))
    return estimados


def migrar():
    store = FileStore()

    # Cargar template real (el ultimo estado guardado)
    template = store.cargar_estado("Chile")
    if template is None or not template.nodos:
        print("ERROR: No hay un estado real de referencia. Ejecuta 'topologia observe' primero.")
        return

    # Cargar historial legacy
    ruta_historial = Path(__file__).resolve().parent.parent / "data" / "topologico" / "historial.json"
    if not ruta_historial.exists():
        print("No se encontro historial.json")
        return

    data = json.loads(ruta_historial.read_text(encoding="utf-8"))
    print(f"Migrando {len(data)} entradas...")

    migradas = 0
    for entry in data:
        estado_str = entry.get("estado", "{}")
        estado_data = json.loads(estado_str)

        # Mapeo: en legacy M_s=social, M_l=logica
        M_m = estado_data.get("M_m", 5.0)
        M_s = estado_data.get("M_s", 5.0)  # social
        M_l = estado_data.get("M_l", 5.0)  # logica
        brecha = estado_data.get("brecha", 0)

        # Estimar nodos
        nodos = estimar_nodos_desde_M(M_m, M_l, M_s, template.nodos)

        # Calcular deltas por nodo
        for n in nodos:
            angulos = calcular_angulos(n.dimension_m, n.dimension_l, n.dimension_s)
            n.delta = calcular_delta(angulos)
            n.fragil = n.delta >= 70

        timestamp_str = entry.get("timestamp", "")
        try:
            fecha = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            fecha = datetime.now()

        estado = EstadoCultural(
            sociedad="Chile",
            nivel_fractal=1,
            fecha=fecha,
            M_m=M_m,
            M_l=M_l,
            M_s=M_s,
            delta_promedio=float(brecha),
            coherente=brecha < 70,
            nodos=nodos,
            nodos_fragiles=[n.nodo_id for n in nodos if n.fragil],
        )

        store.guardar_estado(estado)
        migradas += 1
        print(f"  {fecha.strftime('%Y-%m-%d')}: M=({M_m}, {M_l}, {M_s}) brecha={brecha} -> {len(nodos)} nodos")

    print(f"Migradas {migradas} entradas a FileStore.")


migrar()
