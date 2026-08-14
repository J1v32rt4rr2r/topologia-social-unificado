"""Análisis armónico temporal de las matrices lógicas M (axioma T).

Serie de Fourier discreta sobre muestreo NO uniforme (estados con gaps de
1-4 días) usando el periodograma de Lomb-Scargle, que ajusta por mínimos
cuadrados senos/cosenos a las frecuencias candidatas sin inventar datos.

Teorema de Dirichlet-Jordan: series acotadas y de variación finita (nuestro
caso: M_m/M_l/M_s en [0, 9.9], por tramos monótonos) convergen a la media de
los límites laterales en cada salto y al valor real en continuidad. Esto
garantiza que los coeficientes c_k estén bien definidos.

Salida principal: vector_desarrollo_M — por lógica extrae el periodo y la fase
dominantes (el "vector de desarrollo temporal de las matrices lógicas M").
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence


def frecuencias_candidatas(periodo_min: float, periodo_max: float, n: int) -> list[float]:
    """Grilla log-espaciada de frecuencias (ciclos/día) para periodos en [min, max]."""
    if n < 2 or periodo_min <= 0 or periodo_max <= periodo_min:
        return []
    f_min = 1.0 / periodo_max
    f_max = 1.0 / periodo_min
    log_min = math.log(f_min)
    log_max = math.log(f_max)
    return [math.exp(log_min + (log_max - log_min) * k / (n - 1)) for k in range(n)]


def _media(y: Sequence[float]) -> float:
    return sum(y) / len(y)


def lomb_scargle(
    t: Sequence[float],
    y: Sequence[float],
    frecuencias: Sequence[float],
) -> list[float]:
    """Periodograma de Lomb-Scargle normalizado (potencia de Scargle).

    Los tiempos `t` (en días, relativos) pueden tener gaps: no se interpola.
    La potencia del pico crece con la fuerza de la componente; la significancia
    se evalúa con la relación pico/energía total (`dominancia`).
    """
    n = len(t)
    if n < 3 or len(y) != n or not frecuencias:
        return []
    my = _media(y)
    dy = [v - my for v in y]

    def _sumsq(v: Iterable[float]) -> float:
        return sum(x * x for x in v)

    var = _sumsq(dy) / n
    if var == 0.0:
        return [0.0] * len(frecuencias)

    potencias: list[float] = []
    for f in frecuencias:
        w = 2.0 * math.pi * f
        tau = 0.5 * math.atan2(
            sum(math.sin(2 * w * ti) for ti in t),
            sum(math.cos(2 * w * ti) for ti in t),
        ) / w
        cs = [math.cos(w * (ti - tau)) for ti in t]
        sn = [math.sin(w * (ti - tau)) for ti in t]
        nom = (_sumsq(d * c for d, c in zip(dy, cs)) ** 2 / _sumsq(cs)
               + _sumsq(d * s for d, s in zip(dy, sn)) ** 2 / _sumsq(sn))
        potencias.append(nom / (2.0 * var))
    return potencias


def _refinar_pico(potencias: Sequence[float], frecuencias: Sequence[float]) -> float:
    """Interpolación parabólica sobre log(potencia) para afinar la frecuencia del pico."""
    kmax = max(range(len(potencias)), key=lambda k: potencias[k])
    if kmax == 0 or kmax == len(potencias) - 1:
        return frecuencias[kmax]
    f0, fm, f1 = frecuencias[kmax - 1], frecuencias[kmax], frecuencias[kmax + 1]
    p0, pm, p1 = potencias[kmax - 1], potencias[kmax], potencias[kmax + 1]
    lp0, lpm, lp1 = math.log(p0), math.log(pm), math.log(p1)
    denom = lp0 - 2 * lpm + lp1
    if abs(denom) < 1e-12:
        return fm
    offset = 0.5 * (lp0 - lp1) / denom
    return fm + (f1 - f0) * offset


def vector_desarrollo(
    t: Sequence[float],
    y: Sequence[float],
    periodo_min: float = 2.0,
    periodo_max: float = 30.0,
    n_frecuencias: int = 100,
) -> dict:
    """Vector de desarrollo temporal de una serie irregular.

    Devuelve el periodo dominante T, su amplitud relativa y el desfase (fase
    de la componente a frecuencia dominante). Con pocas muestras (< 6) la
    dominancia es preliminar.
    """
    if len(t) < 3 or len(t) != len(y):
        return {"status": "insuficiente", "n": len(t), "periodo": None,
                "fase": None, "potencia": 0.0, "dominancia": 0.0,
                "r2": 0.0, "confianza_pct": None}

    f = frecuencias_candidatas(periodo_min, periodo_max, n_frecuencias)
    potencias = lomb_scargle(t, y, f)
    if not potencias:
        return {"status": "insuficiente", "n": len(t), "periodo": None,
                "fase": None, "potencia": 0.0, "dominancia": 0.0,
                "r2": 0.0, "confianza_pct": None}

    k_max = max(range(len(potencias)), key=lambda k: potencias[k])
    p_max = potencias[k_max]
    f_pico = _refinar_pico(potencias, f)

    w = 2.0 * math.pi * f_pico
    tau = 0.5 * math.atan2(
        sum(math.sin(2 * w * ti) for ti in t),
        sum(math.cos(2 * w * ti) for ti in t),
    ) / w
    fase = (w * tau) % (2.0 * math.pi)

    potencia_total = sum(potencias) or 1.0
    status = "preliminar" if len(t) < 45 else "estable"
    dominancia = p_max / potencia_total

    # Ajuste a la frecuencia dominante para medir la calidad del modelo armónico.
    modelo = modelo_esperado(t, y, f_pico)
    media = sum(y) / len(y)
    ss_tot = sum((v - media) ** 2 for v in y) or 1e-12
    ss_res = sum((v - e) ** 2 for v, e in zip(y, modelo["esperado"]))
    r2 = max(0.0, 1.0 - ss_res / ss_tot)

    # Confianza de la proyección: pilar la calidad del ajuste (r²), penalizada
    # por falta de muestras (n<45 es preliminar) y por falta de señal rítmica
    # (serie plana → no hay ciclo que proyectar).
    rango = (max(y) - min(y)) or 1e-9
    signal = min(rango / 2.0, 1.0)
    factor_n = min(len(t) / 45.0, 1.0)
    confianza = max(0.0, min(1.0, r2 * factor_n * signal))

    return {
        "status": status,
        "n": len(t),
        "periodo": round(1.0 / f_pico, 2),
        "fase": round(fase, 4),
        "potencia": round(p_max, 4),
        "dominancia": round(dominancia, 4),
        "r2": round(r2, 4),
        "confianza_pct": round(confianza * 100),
    }


def vector_desarrollo_M(
    t: Sequence[float],
    m_m: Sequence[float],
    m_l: Sequence[float],
    m_s: Sequence[float],
) -> dict:
    """Vector de desarrollo temporal de las 3 matrices lógicas M/L/S."""
    return {
        "m": vector_desarrollo(t, m_m),
        "l": vector_desarrollo(t, m_l),
        "s": vector_desarrollo(t, m_s),
    }


def modelo_esperado(
    t: Sequence[float],
    y: Sequence[float],
    frecuencia: float,
) -> dict:
    """Ajusta y_est(t) = c + a·cos(ωt) + b·sin(ωt) por mínimos cuadrados.

    ω = 2π·frecuencia. Devuelve el modelo esperado (coeficientes + curva) para
    evaluar disrupciones: el estado predicho por la componente dominante.

    Returns
    -------
    dict con 'coef' (c, a, b), 'esperado' (lista igual a len(t)), 'periodo'.
    """
    n = len(t)
    w = 2.0 * math.pi * frecuencia
    xs = [math.cos(w * ti) for ti in t]
    ys_ = [math.sin(w * ti) for ti in t]
    ones = [1.0] * n

    def _dot(u: Sequence[float], v: Sequence[float]) -> float:
        return sum(x * z for x, z in zip(u, v))

    diag = [n, _dot(xs, xs), _dot(ys_, ys_)]
    m01 = _dot(ones, xs)
    m02 = _dot(ones, ys_)
    m12 = _dot(xs, ys_)
    b = [_dot(ones, y), _dot(xs, y), _dot(ys_, y)]

    # Sistema simétrico 3x3:  M·coef = b   (M = [(n,m01,m02),(m01,diag1,m12),(m02,m12,diag2)])
    a11, a12, a13 = n, m01, m02
    a21, a22, a23 = m01, diag[1], m12
    a31, a32, a33 = m02, m12, diag[2]
    b1, b2, b3 = b
    det = (a11 * (a22 * a33 - a23 * a32)
           - a12 * (a21 * a33 - a23 * a31)
           + a13 * (a21 * a32 - a22 * a31))
    if abs(det) < 1e-12:
        c = sum(y) / n
        return {"coef": (c, 0.0, 0.0), "esperado": [c] * n, "periodo": round(1.0 / frecuencia, 2)}

    c = ((b1 * (a22 * a33 - a23 * a32)
          - a12 * (b2 * a33 - a23 * b3)
          + a13 * (b2 * a32 - a22 * b3)) / det)
    a = ((a11 * (b2 * a33 - a23 * b3)
          - b1 * (a21 * a33 - a23 * a31)
          + a13 * (a21 * b3 - b2 * a31)) / det)
    bcoef = ((a11 * (a22 * b3 - b2 * a32)
              - a12 * (a21 * b3 - a23 * b1)
              + a13 * (a21 * b2 - a22 * b1)) / det)

    esperado = [c + a * math.cos(w * ti) + bcoef * math.sin(w * ti) for ti in t]
    return {"coef": (c, a, bcoef), "esperado": esperado, "periodo": round(1.0 / frecuencia, 4)}


def disrupcion_temporal(
    t: Sequence[float],
    y: Sequence[float],
    periodo_min: float = 2.0,
    periodo_max: float = 30.0,
    n_frecuencias: int = 100,
    z_umbral: float = 2.0,
) -> dict:
    """Compara el último valor de la serie contra su modelo esperado armónico.

    El orquestador interpreta el vector de desarrollo como lo *esperado*; si el
    valor actual (última muestra) se desvía del modelo por más de `z_umbral`
    desviaciones típicas, se marca como disrupción.

    Returns
    -------
    dict: {status, esperado, actual, residuo, sigma, desvion_normalizada, es_disrupcion}
    """
    if len(t) < 4 or len(t) != len(y):
        return {"status": "insuficiente", "esperado": None, "actual": None,
                "residuo": None, "desvio_normalizado": None, "es_disrupcion": False,
                "r2": 0.0, "dominancia": 0.0, "confianza_proyeccion_pct": None}

    f = frecuencias_candidatas(periodo_min, periodo_max, n_frecuencias)
    potencias = lomb_scargle(t, y, f)
    if not potencias:
        return {"status": "insuficiente", "esperado": None, "actual": None,
                "residuo": None, "desvio_normalizado": None, "es_disrupcion": False,
                "r2": 0.0, "dominancia": 0.0, "confianza_proyeccion_pct": None}

    f_pico = _refinar_pico(potencias, f)
    modelo = modelo_esperado(t, y, f_pico)

    residuos = [v - e for v, e in zip(y, modelo["esperado"])]
    sigma_residual = math.sqrt(sum(r * r for r in residuos) / len(residuos)) or 1e-9

    # Suelo robusto: la desviación mínima interpretable es el 5% del rango de la
    # serie. Evita que el ruido de resolución del modelo (fase del pico) señale
    # disrupciones cuando el ajuste es casi perfecto.
    rango = (max(y) - min(y)) or 1e-9
    sigma = max(sigma_residual, 0.05 * rango)

    actual = y[-1]
    esperado = modelo["esperado"][-1]
    residuo = actual - esperado
    z = residuo / sigma

    # Calidad del modelo armónico a la frecuencia pico.
    media = sum(y) / len(y)
    ss_tot = sum((v - media) ** 2 for v in y) or 1e-12
    ss_res = sum((v - e) ** 2 for v, e in zip(y, modelo["esperado"]))
    r2 = max(0.0, 1.0 - ss_res / ss_tot)
    potencia_total = sum(potencias) or 1.0
    p_max = max(potencias)
    dominancia = p_max / potencia_total

    # Confianza de la proyección: pilar la calidad del ajuste (r²), penalizada
    # por falta de muestras (n<45 es preliminar) y por falta de señal rítmica
    # (serie plana → no hay ciclo que proyectar).
    rango = (max(y) - min(y)) or 1e-9
    signal = min(rango / 2.0, 1.0)
    factor_n = min(len(t) / 45.0, 1.0)
    confianza = max(0.0, min(1.0, r2 * factor_n * signal))

    status = "preliminar" if len(t) < 45 else "estable"
    return {
        "status": status,
        "periodo": modelo["periodo"],
        "esperado": round(esperado, 4),
        "actual": round(actual, 4),
        "residuo": round(residuo, 4),
        "sigma": round(sigma, 4),
        "desvio_normalizado": round(z, 4),
        "es_disrupcion": abs(z) > z_umbral,
        "r2": round(r2, 4),
        "dominancia": round(dominancia, 4),
        "confianza_proyeccion_pct": round(confianza * 100),
    }


def disrupcion_M(
    t: Sequence[float],
    m_m: Sequence[float],
    m_l: Sequence[float],
    m_s: Sequence[float],
    z_umbral: float = 2.0,
) -> dict:
    """Evaluación de disrupción por matriz lógica frente a su modelo esperado."""
    return {
        "m": disrupcion_temporal(t, m_m, z_umbral=z_umbral),
        "l": disrupcion_temporal(t, m_l, z_umbral=z_umbral),
        "s": disrupcion_temporal(t, m_s, z_umbral=z_umbral),
    }


def verificar_suficiencia(
    t: Sequence[float],
    m_m: Sequence[float],
    m_l: Sequence[float],
    m_s: Sequence[float],
    n_min: int = 45,
    ciclos_min: float = 2.0,
) -> dict:
    """Criterio habilitante para el vector de desarrollo y su plano complejo.

    Los puntos 5 (distancias no recíprocas) y 6 (noticia = proyección de la
    lógica del emisor) dependen de la detección fiable del vector de desarrollo
    temporal y su plano complejo (fase). La suficiencia exige que las TRES
    lógicas cumplan el mínimo de muestras y de ciclos del periodo dominante:

      (a) n >= n_min
      (b) span >= ciclos_min * T_k  (ciclos completos por lógica)
      (c) vector_desarrollo.status == "estable"

    Devuelve el estado por lógica y el veredicto habilitante.
    """

    def _por_logica(serie: Sequence[float]) -> dict:
        v = vector_desarrollo(t, serie)
        per = v["periodo"]
        span = t[-1] if t else 0.0
        ciclos = (span / per) if per else 0.0
        return {
            "status": v["status"],
            "periodo": per,
            "ciclos": round(ciclos, 2),
            "n": v["n"],
            "ok": v["n"] >= n_min and ciclos >= ciclos_min,
        }

    por_logica = {
        "m": _por_logica(m_m),
        "l": _por_logica(m_l),
        "s": _por_logica(m_s),
    }
    n = len(t)
    span = t[-1] if n else 0.0
    habilitado = n >= n_min and all(p["ok"] for p in por_logica.values())
    return {
        "habilitado": habilitado,
        "n_muestras": n,
        "span_dias": span,
        "falta_n": max(0, n_min - n),
        "por_logica": por_logica,
        "condiciones": {
            "n_minimo": n_min,
            "ciclos_minimos": ciclos_min,
        },
    }
