"""Worker batch de recolección histórica.
Procesa un periodo por ejecución. Resumible.

Uso:
    python scripts/recoleccion_historica.py               # siguiente pendiente
    python scripts/recoleccion_historica.py --periodo ID  # forzar periodo
    python scripts/recoleccion_historica.py --status      # mostrar cola
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import yaml

_BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE / "src"))

from topologia.logger import logger
from topologia.math.operations import detectar_operaciones
from topologia.orchestrator import Orchestrator
from topologia.web.resumen_historico import recolectar_para_periodo as recolectar_items_para_periodo


# ─── Config ─────────────────────────────────────────────────────────────────

CONFIG_PERIODOS = _BASE / "config" / "periodos_historicos.yaml"
CONFIG_HITOS = _BASE / "config" / "hitos.yaml"
ITEMS_MINIMOS = 10
ITEMS_POR_FUENTE = 20
MAX_TOTAL = 100


# ─── Carga / guardado de config ─────────────────────────────────────────────


def _cargar_yaml(ruta: Path) -> dict:
    if not ruta.exists():
        return {"periodos": []}
    with ruta.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {"periodos": []}


def _guardar_yaml(ruta: Path, data: dict):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _cargar_hitos() -> list[dict]:
    if not CONFIG_HITOS.exists():
        return []
    with CONFIG_HITOS.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _guardar_hito(hito: dict):
    hitos = _cargar_hitos()
    hitos.append(hito)
    with CONFIG_HITOS.open("w", encoding="utf-8") as f:
        yaml.dump(hitos, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


# ─── Estado del worker (resumible) ──────────────────────────────────────────


_ESTADO_WORKER = _BASE / "data" / "historico" / ".worker_state.yaml"


def _guardar_progreso(periodo_id: str, fuente_actual: str, items_actuales: int):
    _ESTADO_WORKER.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "periodo_id": periodo_id,
        "fuente_actual": fuente_actual,
        "items_actuales": items_actuales,
        "timestamp": time.time(),
    }
    _ESTADO_WORKER.write_text(yaml.dump(data), encoding="utf-8")


def _limpiar_progreso():
    if _ESTADO_WORKER.exists():
        _ESTADO_WORKER.unlink()


def _hay_progreso() -> bool:
    return _ESTADO_WORKER.exists()


# ─── Construir hito desde EstadoCultural ────────────────────────────────────


def _estado_a_hito(periodo: dict, items: list, estado, operaciones: list) -> dict:
    nodos_out = {}
    for n in estado.nodos:
        nodos_out[n.nodo_id] = {
            "m": round(n.dimension_m, 1),
            "l": round(n.dimension_l, 1),
            "s": round(n.dimension_s, 1),
            "delta": round(n.delta, 1),
            "fragil": n.fragil,
        }

    ops_activas = []
    for op in operaciones:
        if op.intensidad > 0.3:
            ops_activas.append(op.codigo)

    return {
        "id": periodo["id"],
        "descripcion": periodo.get("descripcion", ""),
        "periodo": {
            "inicio": periodo["fecha_inicio"],
            "fin": periodo["fecha_fin"],
        },
        "recoleccion": {
            "fecha_recoleccion": time.strftime("%Y-%m-%d"),
            "fuentes_usadas": ["duckduckgo"],
            "total_items": len(items),
        },
        "estado": {
            "delta_promedio": round(estado.delta_promedio, 1),
            "M_m": round(estado.M_m, 1),
            "M_l": round(estado.M_l, 1),
            "M_s": round(estado.M_s, 1),
            "coherente": estado.coherente,
            "tension_total": round(estado.tension_total, 1),
            "era_k": estado.era_k,
            "theta_cultura": round(estado.theta_cultura, 1),
            "operaciones": ops_activas,
            "nodos_fragiles": estado.nodos_fragiles,
        },
        "nodos": nodos_out,
    }


# ─── Procesar periodo ────────────────────────────────────────────────────────


def procesar_periodo(periodo: dict) -> bool:
    """Procesa un periodo: recolecta items, observa, guarda hito.
    Retorna True si completó el periodo, False si falló.
    """
    pid = periodo["id"]
    logger.info(f"[{pid}] Iniciando recolección: {periodo.get('descripcion', '')}")

    items = recolectar_items_para_periodo(
        periodo,
        max_items=MAX_TOTAL,
        items_por_query=8,
    )

    if len(items) < ITEMS_MINIMOS:
        logger.warning(
            f"[{pid}] Solo {len(items)} items (mínimo {ITEMS_MINIMOS}). "
            "Se omite este periodo."
        )
        return False

    logger.info(f"[{pid}] {len(items)} items. Ejecutando observe()...")
    orch = Orchestrator()
    try:
        estado = orch.observar("Chile", items=items)
    except Exception as e:
        logger.error(f"[{pid}] observe() falló: {e}")
        return False

    logger.info(f"[{pid}] Detectando operaciones cinéticas...")
    try:
        operaciones = detectar_operaciones(estado)
    except Exception as e:
        logger.warning(f"[{pid}] detectar_operaciones falló: {e}")
        operaciones = []

    logger.info(f"[{pid}] Guardando hito...")
    hito = _estado_a_hito(periodo, items, estado, operaciones)
    _guardar_hito(hito)

    logger.info(f"[{pid}] COMPLETADO. δ={hito['estado']['delta_promedio']}°, "
                f"M=({hito['estado']['M_m']},{hito['estado']['M_l']},{hito['estado']['M_s']})")
    return True


# ─── CLI ─────────────────────────────────────────────────────────────────────


def mostrar_status():
    data = _cargar_yaml(CONFIG_PERIODOS)
    periodos = data.get("periodos", [])
    hitos = _cargar_hitos()
    hitos_ids = {h["id"] for h in hitos}

    print("\n=== COLA DE RECOLECCIÓN HISTÓRICA ===\n")
    if not periodos:
        print("(sin periodos configurados)")
        return

    for p in periodos:
        pid = p["id"]
        completado = p.get("completado", False) or pid in hitos_ids
        activo = p.get("activo", True)
        status = "[COMPLETADO]" if completado else "[PENDIENTE]" if activo else "[INACTIVO]"
        print(f"  {status} {pid}")
        print(f"         {p.get('descripcion', '')}")
        print(f"         {p['fecha_inicio']} → {p['fecha_fin']}")
        print()

    print(f"  Hitos guardados: {len(hitos)}")
    if _hay_progreso():
        prog = yaml.safe_load(_ESTADO_WORKER.read_text())
        print(f"  Worker interrumpido: {prog.get('periodo_id', '?')} "
              f"({prog.get('items_actuales', 0)} items)")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if "--status" in sys.argv:
        mostrar_status()
        return

    data = _cargar_yaml(CONFIG_PERIODOS)
    periodos = data.get("periodos", [])
    hitos = _cargar_hitos()
    hitos_ids = {h["id"] for h in hitos}

    # Si se especificó un periodo, forzarlo
    periodo_forzado = None
    for a in args:
        if a:
            periodo_forzado = a
            break
    if periodo_forzado:
        periodo = next((p for p in periodos if p["id"] == periodo_forzado), None)
        if not periodo:
            print(f"Periodo '{periodo_forzado}' no encontrado")
            mostrar_status()
            sys.exit(1)
        periodos_a_procesar = [periodo]
    else:
        # Encontrar el primer periodo activo no completado
        periodos_a_procesar = [
            p for p in periodos
            if p.get("activo", True) and not p.get("completado", False)
            and p["id"] not in hitos_ids
        ]

    if not periodos_a_procesar:
        print("Todos los periodos están completados. Usa --status para ver la cola.")
        mostrar_status()
        return

    periodo = periodos_a_procesar[0]
    logger.info(f"Procesando: {periodo['id']}")

    ok = procesar_periodo(periodo)

    if ok:
        # Marcar como completado en periodos_historicos.yaml
        for p in data["periodos"]:
            if p["id"] == periodo["id"]:
                p["completado"] = True
                break
        _guardar_yaml(CONFIG_PERIODOS, data)
        _limpiar_progreso()
        print(f"\n✓ Periodo '{periodo['id']}' completado. Hito guardado en {CONFIG_HITOS}")
    else:
        print(f"\n✗ Periodo '{periodo['id']}' falló o no tuvo suficientes datos.")


if __name__ == "__main__":
    main()
