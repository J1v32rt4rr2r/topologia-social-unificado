"""Tests del módulo matemático (orbital 2D, torus 3D y operaciones cinéticas)."""

import math

from topologia.math.operations import detectar_operaciones
from topologia.math.torus import (
    angulo_desde_valor,
    arrastre_gravimetrico,
    calcular_angulos,
    calcular_delta,
    coherencia_global,
    detectar_vuelco,
    mapear_a_toro_3d,
    tension_sistema,
    theta_cultura,
    theta_nodo,
)
from topologia.models.schemas import EstadoCultural, EvaluacionNodo


class TestCalcularAngulos:
    def test_valores_normales(self):
        m, l, s = calcular_angulos(5.0, 5.0, 5.0)
        assert m == 360.0 / 5.0
        assert l == 360.0 / 5.0
        assert s == 360.0 / 5.0

    def test_evita_division_por_cero(self):
        m, l, s = calcular_angulos(0.0, 0.0, 0.0)
        assert m == 360.0 / 0.1
        assert l == 360.0 / 0.1
        assert s == 360.0 / 0.1

    def test_valor_negativo(self):
        m, l, s = calcular_angulos(-1.0, -2.0, -3.0)
        assert m == 360.0 / 0.1
        assert l == 360.0 / 0.1
        assert s == 360.0 / 0.1


class TestCalcularDelta:
    def test_delta_cero(self):
        d = calcular_delta([10.0, 10.0, 10.0])
        assert d == 0.0

    def test_delta_positivo(self):
        d = calcular_delta([10.0, 20.0, 30.0])
        assert d > 0.0

    def test_delta_orden_magnitud(self):
        d = calcular_delta([10.0, 100.0, 200.0])
        media = (10 + 100 + 200) / 3
        var = ((10 - media)**2 + (100 - media)**2 + (200 - media)**2) / 3
        assert d == math.sqrt(var)


class TestMapearToro3D:
    def test_retorna_tupla_cinco_elementos(self):
        resultado = mapear_a_toro_3d(5.0, 5.0, 5.0)
        assert len(resultado) == 5

    def test_intensidad_normalizada(self):
        _, _, _, intensidad, _ = mapear_a_toro_3d(5.0, 5.0, 5.0)
        assert 0.0 <= intensidad <= 1.0

    def test_intensidad_maxima(self):
        _, _, _, intensidad, _ = mapear_a_toro_3d(5.0, 5.0, 9.9)
        assert intensidad == 1.0

    def test_intensidad_cero(self):
        _, _, _, intensidad, _ = mapear_a_toro_3d(0.0, 0.0, 0.0)
        assert intensidad == 0.0


class TestCoherenciaGlobal:
    def test_lista_vacia(self):
        r = coherencia_global([])
        assert r["coherente"] is True

    def test_promedio_correcto(self):
        r = coherencia_global([(5.0, 5.0, 5.0), (7.0, 7.0, 7.0)])
        assert r["M_m"] == 6.0
        assert r["M_l"] == 6.0
        assert r["M_s"] == 6.0

    def test_coherente_si_delta_bajo(self):
        r = coherencia_global([(5.0, 5.0, 5.0), (5.0, 5.0, 5.0)])
        assert r["coherente"] is True
        assert r["nodos_fragiles"] == 0

    def test_incoherente_si_delta_alto(self):
        r = coherencia_global([(9.9, 1.0, 1.0)])
        assert r["coherente"] is False or r["nodos_fragiles"] > 0


def _nodo(nodo_id: str, m: float, l: float, s: float, delta: float = 0) -> EvaluacionNodo:
    return EvaluacionNodo(
        nodo_id=nodo_id,
        nodo_nombre=nodo_id.capitalize(),
        dimension_m=m,
        dimension_l=l,
        dimension_s=s,
        delta=delta,
        fragil=delta >= 70,
    )


# ─── Tests del nuevo modelo orbital ─────────────


class TestAnguloDesdeValor:
    def test_valor_10(self):
        assert angulo_desde_valor(10) == 36.0

    def test_valor_5(self):
        assert angulo_desde_valor(5) == 72.0

    def test_valor_4_punto_8(self):
        assert round(angulo_desde_valor(4.8), 1) == 75.0

    def test_valor_14_punto_4(self):
        assert round(angulo_desde_valor(14.4), 1) == 25.0

    def test_evita_cero(self):
        assert angulo_desde_valor(0) == 3600.0


class TestThetaNodo:
    def test_desde_M_l(self):
        assert theta_nodo(6) == 60.0


class TestThetaCultura:
    def test_promedio(self):
        t = theta_cultura([5, 6, 7])
        esperado = 360.0 / ((5 + 6 + 7) / 3)
        assert t == esperado

    def test_vacio(self):
        assert theta_cultura([]) == 0.0


class TestArrastreGravimetrico:
    def test_arrastre_basico(self):
        a = arrastre_gravimetrico(M_m=8, M_s=9, delta_theta=35)
        assert a == 8 * 9 * 35

    def test_sin_diferencia(self):
        assert arrastre_gravimetrico(5, 5, 0) == 0


class TestTensionSistema:
    def test_tension_total(self):
        nodos = [
            {"dimension_l": 5, "dimension_m": 3},
            {"dimension_l": 9, "dimension_m": 8},
        ]
        t = tension_sistema(nodos)
        assert t > 0

    def test_vacio(self):
        assert tension_sistema([]) == 0.0


class TestDetectarVuelco:
    def test_supera_umbral(self):
        assert detectar_vuelco(900, umbral=500) is True

    def test_no_supera(self):
        assert detectar_vuelco(100, umbral=500) is False


class TestDetectarOperaciones:
    def _estado(self, nodos: list[EvaluacionNodo]) -> EstadoCultural:
        return EstadoCultural(
            sociedad="test",
            M_m=5.0,
            M_l=5.0,
            M_s=5.0,
            delta_promedio=0,
            nodos=nodos,
            nodos_fragiles=[n.nodo_id for n in nodos if n.fragil],
        )

    def test_polarizacion_detectada(self):
        estado = self._estado([_nodo("POLITICA", m=9.0, l=2.0, s=5.0)])
        ops = detectar_operaciones(estado)
        codigos = [o.codigo for o in ops]
        assert "O4a" in codigos

    def test_polarizacion_no_detectada(self):
        estado = self._estado([_nodo("POLITICA", m=5.0, l=5.0, s=5.0)])
        ops = detectar_operaciones(estado)
        assert "O4a" not in [o.codigo for o in ops]

    def test_entropia_con_multiples_bajos(self):
        estado = self._estado([
            _nodo("EDUCACION", m=2.0, l=5.0, s=2.0),
            _nodo("ECONOMIA", m=2.0, l=5.0, s=2.0),
            _nodo("TRABAJO", m=2.0, l=5.0, s=2.0),
        ])
        ops = detectar_operaciones(estado)
        assert "O5" in [o.codigo for o in ops]

    def test_tension_sistemica(self):
        estado = self._estado([
            _nodo("POLITICA", m=1.0, l=9.0, s=1.0, delta=70),
            _nodo("EDUCACION", m=9.0, l=1.0, s=9.0, delta=70),
        ])
        estado.delta_promedio = 50
        ops = detectar_operaciones(estado)
        assert "O1b" in [o.codigo for o in ops]
