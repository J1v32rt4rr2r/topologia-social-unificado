"""Tests de análisis armónico temporal de M (axioma T, serie de Fourier)."""

from __future__ import annotations

import math

from topologia.math.armonicas import (
    disrupcion_M,
    disrupcion_temporal,
    frecuencias_candidatas,
    lomb_scargle,
    modelo_esperado,
    vector_desarrollo,
    vector_desarrollo_M,
    verificar_suficiencia,
)


def _serie_sintetica(periodo: float, n: int = 60) -> tuple[list[float], list[float]]:
    t = [float(i) for i in range(n)]
    y = [6.0 + 2.0 * math.sin(2 * math.pi * ti / periodo) for ti in t]
    return t, y


def _periodo_estimado(p: list[float], fs: list[float]) -> float:
    kmax = max(range(len(p)), key=lambda k: p[k])
    return 1.0 / fs[kmax]


class TestFrecuencias:
    def test_grilla_logaritmica(self):
        freqs = frecuencias_candidatas(2.0, 30.0, 10)
        assert len(freqs) == 10
        assert freqs[0] < freqs[-1]  # ascendente: 1/30 -> 1/2 ciclos/día
        assert abs(freqs[0] - 1.0 / 30.0) < 1e-9
        assert abs(freqs[-1] - 1.0 / 2.0) < 1e-9

    def test_grilla_invalida(self):
        assert frecuencias_candidatas(0.0, 5.0, 5) == []
        assert frecuencias_candidatas(5.0, 5.0, 5) == []


class TestLombScargle:
    def test_pico_en_periodo_conocido(self):
        t, y = _serie_sintetica(periodo=10.0)
        fs = frecuencias_candidatas(2.0, 30.0, 200)
        p = lomb_scargle(t, y, fs)
        estimado = _periodo_estimado(p, fs)
        assert abs(estimado - 10.0) < 0.5
        assert max(p) > 0.8

    def test_irregular_conserva_periodo(self):
        import random

        random.seed(7)
        t, y = [], []
        for i in range(60):
            if random.random() > 0.3:  # gaps aleatorios (~30%)
                t.append(float(i))
                y.append(6.0 + 2.0 * math.sin(2 * math.pi * i / 12.0))
        fs = frecuencias_candidatas(2.0, 30.0, 200)
        p = lomb_scargle(t, y, fs)
        assert abs(_periodo_estimado(p, fs) - 12.0) < 1.0

    def test_insuficiente(self):
        assert lomb_scargle([1.0], [2.0], [0.1]) == []
        assert lomb_scargle([1.0, 2.0], [2.0, 3.0], [0.1]) == []

    def test_serie_plana_sin_pico(self):
        t = list(range(20))
        y = [5.0] * 20
        p = lomb_scargle(t, y, [0.1, 0.2])
        assert p == [0.0, 0.0]


class TestVectorDesarrollo:
    def test_serie_corta_preliminar(self):
        t, y = _serie_sintetica(periodo=8.0, n=30)
        dev = vector_desarrollo(t, y)
        assert dev["status"] == "preliminar"  # n < 45
        assert dev["periodo"] is not None
        assert abs(dev["periodo"] - 8.0) < 1.0
        assert dev["potencia"] > 0.5

    def test_serie_larga_estable(self):
        t, y = _serie_sintetica(periodo=8.0, n=60)
        dev = vector_desarrollo(t, y)
        assert dev["status"] == "estable"  # n >= 45

    def test_insuficiente(self):
        dev = vector_desarrollo([1.0], [3.0])
        assert dev["status"] == "insuficiente"
        assert dev["periodo"] is None


class TestVectorDesarrolloM:
    def test_tres_logica(self):
        t, ym = _serie_sintetica(periodo=12.0)
        _, yl = _serie_sintetica(periodo=9.0)
        _, ys = _serie_sintetica(periodo=7.0)
        dev = vector_desarrollo_M(t, ym, yl, ys)
        assert set(dev.keys()) == {"m", "l", "s"}
        assert all(d["periodo"] is not None for d in dev.values())
        assert abs(dev["m"]["periodo"] - 12.0) < 1.0
        assert abs(dev["s"]["periodo"] - 7.0) < 1.0


class TestModeloEsperado:
    def test_reproduce_suma_senoidal(self):
        t, y = _serie_sintetica(periodo=10.0)
        f = frecuencias_candidatas(2.0, 30.0, 200)
        p = lomb_scargle(t, y, f)
        kmax = max(range(len(p)), key=lambda k: p[k])
        m = modelo_esperado(t, y, f[kmax])
        err = max(abs(a - b) for a, b in zip(y, m["esperado"]))
        assert err < 0.4
        assert m["periodo"] > 0


class TestDisrupcionTemporal:
    def test_serie_coherente_no_disrupcion(self):
        t, y = _serie_sintetica(periodo=12.0)
        d = disrupcion_temporal(t, y)
        assert d["es_disrupcion"] is False

    def test_ultimo_valor_fuera_del_ciclo(self):
        t, y = _serie_sintetica(periodo=12.0)
        y[-1] = y[-1] + 8.0  # desviación clara
        d = disrupcion_temporal(t, y)
        assert d["es_disrupcion"] is True
        assert d["desvio_normalizado"] > 2.0

    def test_insuficiente(self):
        d = disrupcion_temporal([1.0], [3.0])
        assert d["status"] == "insuficiente"
        assert d["es_disrupcion"] is False

    def test_umbral_personalizado(self):
        t, y = _serie_sintetica(periodo=12.0, n=30)
        d_alto = disrupcion_temporal(t, y, z_umbral=10.0)
        assert d_alto["es_disrupcion"] is False


class TestDisrupcionM:
    def test_tres_logica_con_flujo(self):
        t, ym = _serie_sintetica(periodo=12.0)
        _, yl = _serie_sintetica(periodo=9.0)
        _, ys = _serie_sintetica(periodo=7.0)
        d = disrupcion_M(t, ym, yl, ys)
        assert set(d.keys()) == {"m", "l", "s"}
        assert all(not v["es_disrupcion"] for v in d.values())

    def test_detecta_disrupcion_en_una_logica(self):
        t, ym = _serie_sintetica(periodo=12.0)
        _, yl = _serie_sintetica(periodo=9.0)
        _, ys = _serie_sintetica(periodo=7.0)
        ys[-1] = ys[-1] + 9.0
        d = disrupcion_M(t, ym, yl, ys)
        assert d["s"]["es_disrupcion"] is True
        assert d["m"]["es_disrupcion"] is False


class TestIntegracionOrquestador:
    def test_aplica_desarrollo_y_disrupciones(self, tmp_path):
        from datetime import datetime, timedelta

        from topologia.models.schemas import EstadoCultural
        from topologia.orchestrator import Orchestrator
        from topologia.storage.store import FileStore

        store = FileStore(data_dir=str(tmp_path))
        n = 30
        for i in range(n):
            fecha = datetime(2026, 7, 6) + timedelta(days=i)
            v = 6.0 + 2.0 * math.sin(2 * math.pi * i / 12.0)
            if i == n - 1:
                v = v + 9.0  # disrupción en la lógica m al último día
            estado = EstadoCultural(
                sociedad="Chile",
                fecha=fecha,
                m_m=v,
                m_l=6.0 + 2.0 * math.sin(2 * math.pi * i / 9.0),
                m_s=6.0 + 2.0 * math.sin(2 * math.pi * i / 7.0),
            )
            store.guardar_estado(estado)

        orchestrator = Orchestrator.__new__(Orchestrator)
        orchestrator.store = store
        estado_final = store.cargar_estado("Chile")
        assert estado_final is not None

        orchestrator._aplicar_desarrollo_temporal(estado_final, "Chile")

        assert estado_final.desarrollo_m["periodo"] is not None
        assert estado_final.desarrollo_l["periodo"] is not None
        assert estado_final.desarrollo_s["periodo"] is not None
        assert estado_final.disrupcion_m["es_disrupcion"] is True
        assert estado_final.disrupcion_l["es_disrupcion"] is False
        assert estado_final.disrupcion_s["es_disrupcion"] is False
        assert estado_final.disrupcion_detectada is True


class TestVerificarSuficiencia:
    def test_serie_larga_habilitado(self):
        t, ym = _serie_sintetica(periodo=2.1, n=60)
        _, yl = _serie_sintetica(periodo=22.5, n=60)
        _, ys = _serie_sintetica(periodo=12.3, n=60)
        r = verificar_suficiencia(t, ym, yl, ys)
        assert r["habilitado"] is True
        assert all(v["ok"] for v in r["por_logica"].values())

    def test_serie_corta_bloqueado(self) -> None:
        t, ym = _serie_sintetica(periodo=2.1, n=24)
        _, yl = _serie_sintetica(periodo=22.5, n=24)
        _, ys = _serie_sintetica(periodo=12.3, n=24)
        r = verificar_suficiencia(t, ym, yl, ys)
        assert r["habilitado"] is False
        assert r["n_muestras"] == 24
        assert r["falta_n"] == 21

    def test_umbrales_personalizados(self) -> None:
        t, ym = _serie_sintetica(periodo=2.1, n=60)
        _, yl = _serie_sintetica(periodo=22.5, n=60)
        _, ys = _serie_sintetica(periodo=12.3, n=60)
        r = verificar_suficiencia(t, ym, yl, ys, n_min=20, ciclos_min=0.5)
        assert r["habilitado"] is True
        assert r["condiciones"]["n_minimo"] == 20