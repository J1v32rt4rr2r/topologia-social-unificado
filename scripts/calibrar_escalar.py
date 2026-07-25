from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

NODOS_ACTIVOS = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION",
]

CONFIG_HITOS = Path(__file__).resolve().parent.parent / "config" / "hitos.yaml"
CONFIG_ESCALAR = Path(__file__).resolve().parent.parent / "config" / "escalar_riesgo.json"


def _cargar_hitos() -> list[dict]:
    import yaml
    with open(CONFIG_HITOS, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _cargar_config() -> dict:
    with open(CONFIG_ESCALAR, encoding="utf-8") as f:
        return json.load(f)


def _dist_euclidiana(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _componentes_hito(hito: dict) -> dict:
    cfg = _cargar_config()

    nodos = hito["nodos"]
    e = hito["estado"]
    vel = hito.get("velocidades", {})

    vec = [nodos[n]["delta"] for n in NODOS_ACTIVOS]
    hitos_completos = _cargar_hitos()
    max_dist = cfg["componentes"][0]["parametros"]["max_distancia_historica"]
    dists = [_dist_euclidiana(vec, [h["nodos"][n]["delta"] for n in NODOS_ACTIVOS]) for h in hitos_completos if h["id"] != hito["id"]]
    d_prox = 1.0 - (min(dists) / max_dist) if dists else 0.0

    p_m = cfg["componentes"][1]["parametros"]
    suma = e["M_m"] + e["M_l"] + e["M_s"]
    m_cont = 1.0 - (suma - p_m["min_M"]) / (p_m["baseline_M"] - p_m["min_M"])

    p_t = cfg["componentes"][2]["parametros"]
    t_dev = abs(e["theta_cultura"] - p_t["theta_base"]) / p_t["rango_theta"]

    v_trab = vel.get("TRABAJO", {}).get("media", 0)
    max_v = cfg["componentes"][3]["parametros"]["max_v_historica"]
    v_trab_n = min(abs(v_trab) / max_v, 1.0) if max_v else 0.0

    max_s = cfg["componentes"][4]["parametros"]["max_delta_historica"]
    s_act = min(nodos.get("SEXUALIDAD", {}).get("delta", 0) / max_s, 1.0) if max_s else 0.0

    co_sync = 0.0
    sync_nodos = cfg["componentes"][5]["parametros"]["nodos"]
    vals = [nodos.get(n, {}).get("delta", 0) for n in sync_nodos]
    n = len(vals)
    if n >= 3:
        m = sum(vals) / n
        num = sum((v - m) ** 2 for v in vals)
        den = math.sqrt(num * (n - 1)) if num > 0 else 1
        co_sync = 1.0 - math.sqrt(sum((v - m) ** 2 for v in vals) / n) / (max(vals) + 0.01) if max(vals) > 0 else 0.0

    return {
        "delta_proximidad": max(0, min(1, d_prox)),
        "m_contraccion": max(0, min(1, m_cont)),
        "theta_desviacion": max(0, min(1, t_dev)),
        "v_trabajo_norm": v_trab_n,
        "s_activacion": s_act,
        "co_sincronia": max(0, min(1, co_sync)),
    }


def _pesos_correlacion(X: list[list[float]], y: list[float]) -> list[float]:
    n_vars = len(X[0])
    n_obs = len(X)
    corrs = []
    for j in range(n_vars):
        xj = [X[i][j] for i in range(n_obs)]
        mx, my = sum(xj) / n_obs, sum(y) / n_obs
        num = sum((xj[i] - mx) * (y[i] - my) for i in range(n_obs))
        den = math.sqrt(sum((xj[i] - mx) ** 2 for i in range(n_obs)) * sum((y[i] - my) ** 2 for i in range(n_obs)))
        r = num / den if den else 0
        corrs.append(max(0, r))
    suma = sum(corrs)
    return [c / suma for c in corrs] if suma > 0 else [1.0 / n_vars] * n_vars


def calibrar():
    print("=== CALIBRACION DEL ESCALAR DE RIESGO ===\n")

    hitos = _cargar_hitos()
    cfg = _cargar_config()
    comp_ids = [c["id"] for c in cfg["componentes"]]

    print(f"Hitos: {len(hitos)}")
    print(f"Componentes: {comp_ids}\n")

    matriz = []
    targets = []
    for h in hitos:
        comps = _componentes_hito(h)
        vec = [comps[cid] for cid in comp_ids]
        matriz.append(vec)
        targets.append(h["estado"]["delta_promedio"] / 10.0)
        print(f"  {h['id']:30s}  comps={[f'{v:.3f}' for v in vec]}  target={targets[-1]:.3f}")

    print("\n--- Correlacion de cada componente con delta_promedio ---")
    pesos_corr = _pesos_correlacion(matriz, targets)
    for cid, p in zip(comp_ids, pesos_corr):
        print(f"  {cid:25s}  peso_correlacion={p:.4f}")
    print("\n  Usando pesos uniformes (mas robusto con n=7):")
    n = len(comp_ids)
    pesos = [1.0 / n] * n
    pesos_dict = {cid: round(p, 4) for cid, p in zip(comp_ids, pesos)}
    print(f"  Pesos optimizados: {pesos_dict}")

    print("\n--- Leave-one-out ---")
    errores = []
    for i, h in enumerate(hitos):
        train_X = [matriz[j] for j in range(len(hitos)) if j != i]
        train_y = [targets[j] for j in range(len(hitos)) if j != i]
        test_X = matriz[i]
        test_y = targets[i]

        w = [1.0 / len(comp_ids)] * len(comp_ids)

        R_pred = sum(w[j] * test_X[j] for j in range(len(w)))
        error = abs(R_pred - test_y)
        errores.append(error)

        print(f"  Excluyendo {h['id']:25s}  R_pred={R_pred:.3f}  R_real={test_y:.3f}  error={error:.3f}")

    mae = sum(errores) / len(errores)
    rmse = math.sqrt(sum(e ** 2 for e in errores) / len(errores))
    print(f"\n  MAE: {mae:.4f}")
    print(f"  RMSE: {rmse:.4f}")

    print("\n--- Prediccion R vs target ---")
    for i, h in enumerate(hitos):
        R = sum(pesos[j] * matriz[i][j] for j in range(len(pesos)))
        t = targets[i] * 10
        r_scaled = R * 10
        print(f"  {h['id']:30s}  R={r_scaled:.2f}  delta_real={t:.1f}  dif={abs(r_scaled-t):.1f}")

    print(f"\n--- Actualizando {CONFIG_ESCALAR} ---")
    with open(CONFIG_ESCALAR, encoding="utf-8") as f:
        cfg_full = json.load(f)
    cfg_full["pesos_iniciales"] = pesos_dict
    cfg_full["calibracion"] = {
        "fecha": str(Path(__file__).stat().st_mtime),
        "mae_leave_one_out": round(mae, 4),
        "rmse_leave_one_out": round(rmse, 4),
        "metodo": "pesos_uniformes_con_diagnostico_correlacion",
        "n_hitos": len(hitos),
    }
    with open(CONFIG_ESCALAR, "w", encoding="utf-8") as f:
        json.dump(cfg_full, f, ensure_ascii=False, indent=2)
    print(f"  Pesos guardados: {pesos_dict}")
    print("  Listo.")


if __name__ == "__main__":
    calibrar()
