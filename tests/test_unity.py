"""Tests del núcleo del ente fractal (Axiomas U, F, O, D)."""

import cmath
import math

from topologia.math.unity import (
    arrastre,
    densidad,
    diferencia_angular,
    estado_falsificable,
    estado_operativo,
    fase_dominante,
    identidad,
    inversa_negativa,
    mapeo_valoracion,
    tecelado,
)
from topologia.models.schemas import EvaluacionNodo


def _nodo(nodo_id: str, m: float, l_: float, s: float) -> EvaluacionNodo:
    return EvaluacionNodo(
        nodo_id=nodo_id,
        nodo_nombre=nodo_id.capitalize(),
        dimension_m=m,
        dimension_l=l_,
        dimension_s=s,
    )


class TestUnidad:
    def test_identidad_es_uno(self):
        assert identidad() == 1.0 + 0j

    def test_falsificable_entero_colapsa_a_identidad(self):
        assert abs(estado_falsificable(2) - 1.0) < 1e-9

    def test_falsificable_modulo_unitario(self):
        assert abs(abs(estado_falsificable(3.7)) - 1.0) < 1e-9

    def test_operativo_cuatro_es_imaginario(self):
        p = estado_operativo(4)
        assert abs(p - 1j) < 1e-9

    def test_operativo_modulo_unitario(self):
        assert abs(abs(estado_operativo(9.9)) - 1.0) < 1e-9


class TestInversaNegativa:
    def test_reciproca_negativa(self):
        assert abs(inversa_negativa(-4.0) - 0.25) < 1e-12
        assert abs(inversa_negativa(2.0) + 0.5) < 1e-12

    def test_involucion(self):
        for x in (3.0, -5.0, 0.25, -0.1):
            assert abs(inversa_negativa(inversa_negativa(x)) - x) < 1e-9

    def test_cero_indefinido(self):
        try:
            inversa_negativa(0.0)
        except ValueError:
            return
        raise AssertionError("inversa_negativa(0) debería lanzar ValueError")


class TestMapeoValoracion:
    def test_angulo_y_punto(self):
        theta, p = mapeo_valoracion(10)
        assert theta == 36.0
        assert abs(p - cmath.exp(1j * math.radians(36.0))) < 1e-12

    def test_deficiente_angulo_alto(self):
        theta, _ = mapeo_valoracion(1.0)
        assert theta == 360.0

    def test_evita_division_cero(self):
        theta, p = mapeo_valoracion(0.0)
        assert theta == 3600.0
        assert abs(abs(p) - 1.0) < 1e-9


class TestTecelado:
    NODOS = ["ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA", "LENGUAJE",
             "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION"]

    def test_27_vertices(self):
        t = tecelado([_nodo(n, 5.0, 5.0, 5.0) for n in self.NODOS])
        assert len(t) == 27

    def test_vertices_en_circulo_unitario(self):
        t = tecelado([_nodo("ECONOMIA", 3.2, 5.0, 8.0)])
        for p in t.values():
            assert abs(abs(p) - 1.0) < 1e-9

    def test_claves_nodo_canal(self):
        t = tecelado([_nodo("ECONOMIA", 3.2, 5.0, 8.0)])
        assert set(t.keys()) == {"ECONOMIA:M", "ECONOMIA:L", "ECONOMIA:S"}


class TestFaseDominante:
    def test_canal_maximo(self):
        k, theta = fase_dominante(5.0, 6.0, 9.0)
        assert k == "S"
        assert theta == 40.0

    def test_empate_primero(self):
        k, _ = fase_dominante(8.0, 8.0, 5.0)
        assert k == "M"

    def test_evita_division_cero(self):
        _, theta = fase_dominante(0.0, 0.0, 0.0)
        assert theta == 3600.0


class TestDensidad:
    def test_cluster_perfecto(self):
        nucleo = 1.0 + 0j
        d = densidad([nucleo, nucleo, nucleo], nucleo)
        assert d["R"] > 0.99
        assert d["D"] == 1.0

    def test_uniforme_r_bajo(self):
        nucleo = 1.0 + 0j
        puntos = [cmath.exp(1j * math.radians(a)) for a in range(0, 360, 45)]
        d = densidad(puntos, nucleo)
        assert d["R"] < 0.5

    def test_ventana_estrecha(self):
        nucleo = 1.0 + 0j
        puntos = [cmath.exp(1j * math.radians(a)) for a in (0, 5, 10, 100, 200)]
        d = densidad(puntos, nucleo, eps=30.0)
        assert d["D"] == 3 / 5

    def test_vacio(self):
        d = densidad([], 1.0 + 0j)
        assert d == {"R": 0.0, "D": 0.0, "n": 0}


class TestArrastre:
    def test_sin_desalineacion_no_arrastra(self):
        nucleo = cmath.exp(1j * 1.0)
        assert abs(arrastre(nucleo, nucleo, 0.9, 0.0) - nucleo) < 1e-12

    def test_arrastre_acerca_al_nucleo(self):
        nucleo = 1j
        p = 1.0 + 0j
        p_ef = arrastre(p, nucleo, 0.9, math.pi / 2)
        assert diferencia_angular(p_ef, nucleo) < diferencia_angular(p, nucleo)

    def test_sin_densidad_no_arrastra(self):
        p = 1.0 + 0j
        assert abs(arrastre(p, 1j, 0.0, math.pi) - p) < 1e-12
