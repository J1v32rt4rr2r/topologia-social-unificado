"""Genera series temporales internas de cada hito con 5 snapshots cada 3 días.

Uso:
    python scripts/serie_hito.py --hito estallido_2019
    python scripts/serie_hito.py --hito pandemia_ola1_2020
    python scripts/serie_hito.py --all          # todos los hitos
    python scripts/serie_hito.py --status       # mostrar qué falta
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml

_BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE / "src"))

from topologia.logger import logger
from topologia.math.operations import detectar_operaciones
from topologia.orchestrator import Orchestrator
from topologia.web.resumen_historico import recolectar_para_periodo as recolectar_items_para_periodo

# ─── Config ─────────────────────────────────────────────────────────────────

CONFIG_HITOS = _BASE / "config" / "hitos.yaml"
ITEMS_POR_SNAPSHOT = 30
MAX_TOTAL = 50
INTERVALO_DIAS = 3
SNAPSHOTS_POR_HITO = 5

NODOS = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA", "LENGUAJE",
    "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]


# ─── Carga / guardado ────────────────────────────────────────────────────────


def _cargar_hitos() -> list[dict]:
    if not CONFIG_HITOS.exists():
        return []
    with CONFIG_HITOS.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _guardar_hitos(hitos: list[dict]):
    with CONFIG_HITOS.open("w", encoding="utf-8") as f:
        yaml.dump(hitos, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _snapshot_key(hito_id: str, fecha: str) -> str:
    return f"{hito_id}__{fecha}"


# ─── Generar fechas de snapshots ─────────────────────────────────────────────


def generar_fechas_snapshot(periodo: dict) -> list[str]:
    inicio_str = periodo.get("fecha_inicio") or periodo.get("inicio")
    fin_str = periodo.get("fecha_fin") or periodo.get("fin")
    if not inicio_str or not fin_str:
        return []
    inicio = datetime.strptime(inicio_str, "%Y-%m-%d")
    fin = datetime.strptime(fin_str, "%Y-%m-%d")

    fechas = []
    current = inicio
    for _ in range(SNAPSHOTS_POR_HITO):
        if current > fin:
            break
        fechas.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=INTERVALO_DIAS)
    return fechas


# ─── Construir snapshot desde EstadoCultural ──────────────────────────────────


def _estado_a_snapshot(estado) -> dict:
    nodos_out = {}
    for n in estado.nodos:
        nodos_out[n.nodo_id] = {
            "m": round(n.dimension_m, 1),
            "l": round(n.dimension_l, 1),
            "s": round(n.dimension_s, 1),
            "delta": round(n.delta, 1),
        }
    return {
        "estado": {
            "delta_promedio": round(estado.delta_promedio, 1),
            "M_m": round(estado.M_m, 1),
            "M_l": round(estado.M_l, 1),
            "M_s": round(estado.M_s, 1),
        },
        "nodos": nodos_out,
    }


# ─── Calcular velocidad y dirección ───────────────────────────────────────────


def calcular_velocidades(serie: list[dict]) -> list[dict]:
    velocidades = {}
    for n in NODOS:
        deltas = [s["nodos"][n]["delta"] for s in serie]
        vals = []
        for k in range(len(deltas) - 1):
            v = (deltas[k + 1] - deltas[k]) / INTERVALO_DIAS
            vals.append(round(v, 2))
        media = sum(vals) / len(vals) if vals else 0
        max_v = max(vals, key=abs) if vals else 0
        aceleracion = None
        if len(vals) >= 2:
            aceleracion = round((vals[-1] - vals[0]) / (len(vals) * INTERVALO_DIAS), 3)
        velocidades[n] = {
            "valores": vals,
            "media": round(media, 3),
            "max": round(max_v, 3),
            "direccion": "+" if media >= 0 else "-",
            "aceleracion": aceleracion,
            "delta_inicial": deltas[0],
            "delta_final": deltas[-1],
        }
    return velocidades


# ─── Procesar un snapshot individual ──────────────────────────────────────────


def procesar_snapshot(hito_id: str, fecha: str) -> dict | None:
    periodo = {
        "id": hito_id,
        "fecha_inicio": fecha,
        "fecha_fin": fecha,
        "descripcion": f"Snapshot {fecha}",
    }
    logger.info(f"  [{hito_id}] Snapshot {fecha}: recolectando...")
    items = recolectar_items_para_periodo(
        periodo,
        max_items=MAX_TOTAL,
        items_por_query=6,
    )
    if len(items) < 5:
        logger.warning(f"  [{hito_id}] Snapshot {fecha}: solo {len(items)} items, se omite")
        return None
    logger.info(f"  [{hito_id}] Snapshot {fecha}: {len(items)} items, observe()...")
    orch = Orchestrator()
    try:
        estado = orch.observar("Chile", items=items)
    except Exception as e:
        logger.error(f"  [{hito_id}] Snapshot {fecha} observe() falló: {e}")
        return None
    snap = _estado_a_snapshot(estado)
    snap["fecha"] = fecha
    snap["total_items"] = len(items)
    logger.info(f"  [{hito_id}] Snapshot {fecha}: delta={snap['estado']['delta_promedio']}")
    return snap


# ─── Procesar un hito completo ────────────────────────────────────────────────


def tiene_serie_completa(hito: dict) -> bool:
    serie = hito.get("serie", [])
    fechas_esperadas = generar_fechas_snapshot(hito["periodo"])
    fechas_reales = {s.get("fecha") for s in serie}
    esperadas = set(fechas_esperadas)
    return len(esperadas - fechas_reales) == 0


def procesar_hito(hito: dict) -> bool:
    pid = hito["id"]
    logger.info(f"[{pid}] Iniciando serie de {SNAPSHOTS_POR_HITO} snapshots cada {INTERVALO_DIAS}d")

    if tiene_serie_completa(hito):
        logger.info(f"[{pid}] Serie ya completa ({len(hito.get('serie',[]))} snapshots)")
        return True

    fechas = generar_fechas_snapshot(hito["periodo"])
    logger.info(f"[{pid}] Ventana: {hito['periodo'].get('inicio','?')} → {hito['periodo'].get('fin','?')}")
    logger.info(f"[{pid}] Fechas snapshot: {fechas}")

    if pid == "plebiscito_1988":
        logger.info(f"[{pid}] Hito manual, no se puede recolectar serie")
        return False

    serie_existente = {s.get("fecha") for s in hito.get("serie", [])}
    snapshots = [s for s in hito.get("serie", []) if s.get("fecha") not in [None, ""]]

    for fecha in fechas:
        if fecha in serie_existente:
            logger.info(f"[{pid}] Snapshot {fecha} ya existe, saltando")
            continue
        snap = procesar_snapshot(pid, fecha)
        if snap is None:
            continue
        snapshots.append(snap)

        # Guardar progreso intermedio
        hitos = _cargar_hitos()
        for h in hitos:
            if h["id"] == pid:
                h["serie"] = snapshots
                velocidades = calcular_velocidades(snapshots)
                if velocidades:
                    h["velocidades"] = velocidades
                break
        _guardar_hitos(hitos)

    if len(snapshots) >= 2:
        velocidades = calcular_velocidades(snapshots)
        hitos = _cargar_hitos()
        for h in hitos:
            if h["id"] == pid:
                h["serie"] = snapshots
                h["velocidades"] = velocidades
                break
        _guardar_hitos(hitos)
        logger.info(f"[{pid}] Velocidades calculadas para {len(snapshots)} snapshots")
        for n, v in velocidades.items():
            if abs(v["media"]) > 0.5:
                logger.info(f"  {n:15s} v={v['media']:+.3f} δ/día  dir={v['direccion']}  acel={v['aceleracion']}")

    logger.info(f"[{pid}] Serie completada: {len(snapshots)}/{SNAPSHOTS_POR_HITO} snapshots")
    return len(snapshots) >= 2


# ─── CLI ─────────────────────────────────────────────────────────────────────


def mostrar_status():
    hitos = _cargar_hitos()
    print("\n=== SERIES DE HITOS ===\n")
    for h in hitos:
        serie = h.get("serie", [])
        if not serie:
            fechas = generar_fechas_snapshot(h["periodo"])
            for f in fechas:
                print(f"  [PENDIENTE] {h['id']} → {f}")
        else:
            vel = h.get("velocidades", {})
            nodos_activos = {n for n, v in vel.items() if abs(v.get("media", 0)) > 0.3} if vel else set()
            print(f"  [OK] {h['id']}: {len(serie)} snapshots, {len(nodos_activos)} nodos con movimiento")
            for s in serie:
                print(f"         {s.get('fecha','?'):12s} δ={s['estado']['delta_promedio']}")
    print()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if "--status" in sys.argv:
        mostrar_status()
        return

    hitos = _cargar_hitos()
    if not hitos:
        print("No hay hitos cargados.")
        return

    if "--all" in sys.argv:
        a_procesar = hitos
    elif args:
        pid = args[0]
        a_procesar = [h for h in hitos if h["id"] == pid]
        if not a_procesar:
            print(f"Hito '{pid}' no encontrado")
            mostrar_status()
            return
    else:
        # Primer hito sin serie completa
        a_procesar = [h for h in hitos if not tiene_serie_completa(h)]
        if not a_procesar:
            print("Todos los hitos tienen serie completa")
            return
        a_procesar = [a_procesar[0]]

    for h in a_procesar:
        if h["id"] == "plebiscito_1988":
            print(f"  {h['id']}: hito manual, saltando...")
            continue
        ok = procesar_hito(h)
        if ok:
            print(f"  ✓ {h['id']} completado")
        else:
            print(f"  ✗ {h['id']} falló o incompleto")


if __name__ == "__main__":
    main()
