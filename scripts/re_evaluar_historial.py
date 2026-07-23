"""
Re-evalúa todos los estados históricos con los parámetros actuales
(temperatura 0.7, prompts suaves, keywords expandidas) para
garantizar consistencia en la serie temporal.

Uso:  python -m scripts.re_evaluar_historial
"""

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from topologia.agents.estadista import Estadista
from topologia.agents.filosofo import Filosofo
from topologia.agents.sociologo import Sociologo
from topologia.logger import logger
from topologia.math.operations import detectar_operaciones
from topologia.math.torus import (
    calcular_angulos,
    calcular_delta,
    coherencia_formas,
    coherencia_global,
    detectar_vuelco,
    forma_cultural_compleja,
    forma_transversal,
    tension_sistema,
    theta_cultura,
)
from topologia.models.schemas import EstadoCultural, EvaluacionNodo
from topologia.storage.store import FileStore
from topologia.web.brechas import NODOS_CULTURALES, terminos_para_nodo
from topologia.web.rss import obtener_items as obtener_items_rss
from topologia.web.bcn import obtener_items as obtener_items_bcn
from topologia.web.resumen import obtener_items as obtener_items_resumen
from topologia.web.youtube import buscar as buscar_youtube
from topologia.web.tendencias import obtener_tendencias
from topologia.web.espectro_b import obtener_items as obtener_items_espectro_b


def _fetch_items():
    items = obtener_items_rss(limite=20)
    items += obtener_items_bcn(limite=3)
    items += obtener_items_resumen(limite=10)
    try:
        items_eb = obtener_items_espectro_b(limite_por_medio=3)
        if items_eb:
            items.extend(items_eb)
    except Exception as e:
        logger.warning(f"espectro_b falló: {e}")
    try:
        items_yt = buscar_youtube(query="Chile", max_resultados=10)
        if items_yt:
            items.extend(items_yt)
    except Exception as e:
        logger.warning(f"youtube falló: {e}")
    try:
        items_tr = obtener_tendencias(max_items=10)
        if items_tr:
            items.extend(items_tr)
    except Exception as e:
        logger.warning(f"tendencias falló: {e}")
    logger.info(f"Total items obtenidos: {len(items)}")
    return items


def re_evaluar_historial(sociedad: str = "Chile"):
    store = FileStore()
    base_dir = Path(store.base) / "estados"
    backup_dir = Path(store.base) / "estados_backup_pre_reeval"

    # Backup y carga de estados originales
    estados_originales: dict[str, EstadoCultural] = {}
    if not backup_dir.exists() and base_dir.exists():
        backup_dir.mkdir(parents=True)
        for f in sorted(base_dir.glob(f"{sociedad}_*.json")):
            estado_orig = store.cargar_estado(sociedad, f.stem.split("_", 1)[1])
            if estado_orig:
                estados_originales[estado_orig.fecha.strftime("%Y-%m-%d")] = estado_orig
            f.rename(backup_dir / f.name)
        logger.info(f"Estados respaldados en {backup_dir} ({len(estados_originales)} cargados)")
    elif backup_dir.exists():
        for f in sorted(backup_dir.glob(f"{sociedad}_*.json")):
            import json
            from topologia.models.schemas import EstadoCultural as EC
            data = json.loads(f.read_text(encoding="utf-8"))
            fecha_str = f.stem.split("_", 1)[1]
            try:
                estado = EC.model_validate(data)
                estados_originales[fecha_str] = estado
            except Exception as e:
                logger.warning(f"Error cargando backup {f.name}: {e}")
        fechas = sorted(estados_originales.keys())
        logger.info(f"Cargados {len(estados_originales)} estados desde backup: {', '.join(fechas)}")
    else:
        logger.warning("No hay estados originales ni backup. Abortando.")
        return

    if not estados_originales:
        logger.error("No se pudo cargar ningún estado original. Abortando.")
        return

    fechas = sorted(estados_originales.keys())

    items = _fetch_items()
    estadista = Estadista()
    filosofo = Filosofo()
    sociologo = Sociologo()
    estado_anterior: EstadoCultural | None = None

    for i, fecha_str in enumerate(fechas):
        logger.info(f"[{i+1}/{len(fechas)}] Procesando {fecha_str}...")

        # Cargar el estado original para obtener valores de fecha/era_k originales
        estado_original = estados_originales.get(fecha_str)
        if estado_original is None:
            logger.warning(f"No se pudo cargar {fecha_str}, se salta")
            continue

        # Si no hay estado_anterior, usar el mismo original como referencia
        ref = estado_anterior or estado_original

        evaluaciones: list[EvaluacionNodo] = []
        for nodo_id in NODOS_CULTURALES:
            score_anterior_m = 5.0
            score_anterior_l = 5.0
            score_anterior_s = 5.0
            just_anterior_m = ""
            just_anterior_l = ""
            just_anterior_s = ""

            if ref:
                for n in ref.nodos:
                    if n.nodo_id == nodo_id:
                        score_anterior_m = n.dimension_m
                        score_anterior_l = n.dimension_l
                        score_anterior_s = n.dimension_s
                        just_anterior_m = n.justificacion_m
                        just_anterior_l = n.justificacion_l
                        just_anterior_s = n.justificacion_s

            terminos = terminos_para_nodo(nodo_id)
            items_filtrados = [
                it for it in items
                if any(t in (it.titulo + it.contenido).lower() for t in terminos)
            ]
            items_filtrados = items_filtrados or items[:5]

            try:
                eval_m = estadista.evaluar_nodo(nodo_id, items_filtrados, score_anterior_m, just_anterior_m)
            except Exception as e:
                logger.error(f"Estadista falló en {nodo_id}/{fecha_str}: {e}")
                eval_m = type("_Eval", (), {"dimension_m": score_anterior_m, "justificacion_m": "", "tendencia_m": "estable"})()

            try:
                eval_l = filosofo.evaluar_nodo(nodo_id, items_filtrados, score_anterior_l, just_anterior_l)
            except Exception as e:
                logger.error(f"Filosofo falló en {nodo_id}/{fecha_str}: {e}")
                eval_l = type("_Eval", (), {"dimension_l": score_anterior_l, "justificacion_l": "", "tendencia_l": "estable"})()

            try:
                eval_s = sociologo.evaluar_nodo(nodo_id, items_filtrados, score_anterior_s, just_anterior_s)
            except Exception as e:
                logger.error(f"Sociologo falló en {nodo_id}/{fecha_str}: {e}")
                eval_s = type("_Eval", (), {"dimension_s": score_anterior_s, "justificacion_s": "", "tendencia_s": "estable"})()

            evaluacion = EvaluacionNodo(
                nodo_id=nodo_id,
                nodo_nombre=nodo_id.capitalize(),
                dimension_m=eval_m.dimension_m,
                dimension_l=eval_l.dimension_l,
                dimension_s=eval_s.dimension_s,
                justificacion_m=eval_m.justificacion_m,
                justificacion_l=eval_l.justificacion_l,
                justificacion_s=eval_s.justificacion_s,
                tendencia_m=eval_m.tendencia_m,
                tendencia_l=eval_l.tendencia_l,
                tendencia_s=eval_s.tendencia_s,
                score_anterior_m=score_anterior_m,
                score_anterior_l=score_anterior_l,
                score_anterior_s=score_anterior_s,
            )
            evaluaciones.append(evaluacion)

        # Métricas globales
        vals = [(n.dimension_m, n.dimension_l, n.dimension_s) for n in evaluaciones]
        coh = coherencia_global(vals)

        nodos_ml = [n.dimension_l for n in evaluaciones]
        t_cultura = theta_cultura(nodos_ml)

        for n in evaluaciones:
            n.delta = calcular_delta(calcular_angulos(n.dimension_m, n.dimension_l, n.dimension_s))
            n.fragil = n.delta >= 70

        tension = tension_sistema([
            {"dimension_l": n.dimension_l, "dimension_m": n.dimension_m} for n in evaluaciones
        ])

        era_k = 1
        if ref:
            era_k = ref.era_k + (1 if detectar_vuelco(tension, umbral=800.0) else 0)

        estado = EstadoCultural(
            sociedad=sociedad,
            fecha=estado_original.fecha,
            M_m=round(coh["M_m"], 1),
            M_l=round(coh["M_l"], 1),
            M_s=round(coh["M_s"], 1),
            delta_promedio=round(coh["delta_promedio"], 1),
            coherente=coh["coherente"],
            nodos=evaluaciones,
            nodos_fragiles=[n.nodo_id for n in evaluaciones if n.fragil],
            era_k=era_k,
            theta_cultura=round(t_cultura, 1),
            tension_total=round(tension, 1),
            vuelco_detectado=era_k > (ref.era_k if ref else 0),
        )

        # Formas culturales complejas
        for dim_key, attr_m, attr_theta in [
            ("m", "m_m", "theta_m"),
            ("l", "m_l", "theta_l"),
            ("s", "m_s", "theta_s"),
        ]:
            vals_dim = [getattr(n, f"dimension_{dim_key}") / 9.9 for n in evaluaciones]
            ft = forma_transversal(vals_dim)
            setattr(estado, attr_m, round(ft["M"], 3))
            setattr(estado, attr_theta, round(math.degrees(ft["angulo"]), 1))

        Fs = [forma_cultural_compleja(getattr(estado, f"m_{d}")) for d in ("m", "l", "s")]
        estado.coherencia_interna = round(math.degrees(coherencia_formas(Fs)), 1)

        # Cambiar fecha explícitamente para que el nombre de archivo sea el histórico
        guardar_con_fecha(store, estado, fecha_str)
        estado_anterior = estado
        logger.info(f"  → {fecha_str}: δ={estado.delta_promedio:.1f}°, M=({estado.M_m},{estado.M_l},{estado.M_s}), era_k={era_k}")

        # Pausa entre estados
        if i < len(fechas) - 1:
            time.sleep(2)

    logger.info("Re-evaluación completada. Reconstruyendo timeline...")

    # Reconstruir timeline y gráficos
    try:
        from scripts.barrido_timeline import actualizar_timeline
        actualizar_timeline(sociedad)
    except Exception as e:
        logger.warning(f"actualizar_timeline falló: {e}")

    try:
        from scripts.graficos_timeline import generar_todos as generar_timeline
        generar_timeline(items_por_nodo=None)
    except Exception as e:
        logger.warning(f"generar_timeline falló: {e}")

    logger.info("Done.")


def guardar_con_fecha(store: FileStore, estado: EstadoCultural, fecha_str: str):
    """Guarda el estado usando fecha_str como nombre de archivo, no la fecha del objeto."""
    from datetime import datetime
    base_dir = Path(store.base)
    ruta = base_dir / "estados" / f"{estado.sociedad}_{fecha_str}.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    import json
    data = estado.model_dump(mode="json")
    data["fecha"] = f"{fecha_str}T12:00:00"
    ruta.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S")
    re_evaluar_historial()
