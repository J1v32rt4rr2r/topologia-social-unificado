from datetime import datetime
from unittest.mock import patch

from topologia.web.compuestos import (
    actualizar_termino,
    cargar_combinaciones,
    frases_para_nodo,
    frases_para_pareja,
)


class TestCargarCombinaciones:
    def test_carga_desde_yaml(self):
        combos = cargar_combinaciones()
        assert len(combos) >= 20
        for combo in combos:
            assert len(combo["nodos"]) == 2
            assert combo["frases"]

    def test_incluye_ejemplos_del_usuario(self):
        combos = cargar_combinaciones()
        parejas = [tuple(combo["nodos"]) for combo in combos]
        assert ("POLITICA", "ECONOMIA") in parejas
        assert ("EDUCACION", "SEXUALIDAD") in parejas
        assert ("POLITICA", "RELIGION") in parejas


class TestFrasesParaNodo:
    def test_politica_incluye_economica_y_religiosa(self):
        frases = frases_para_nodo("POLITICA")
        assert "política económica" in frases
        assert "política religiosa" in frases
        assert "discurso político" in frases

    def test_economia_incluye_politica_economica(self):
        frases = frases_para_nodo("ECONOMIA")
        assert "política económica" in frases

    def test_educacion_incluye_educacion_sexual(self):
        frases = frases_para_nodo("EDUCACION")
        assert "educación sexual" in frases

    def test_sin_duplicados(self):
        frases = frases_para_nodo("ECONOMIA")
        assert len(frases) == len(set(frases))

    def test_max_frases(self):
        frases = frases_para_nodo("POLITICA", max_frases=2)
        assert len(frases) == 2

    def test_nodo_sin_combinaciones(self):
        assert frases_para_nodo("NODO_SIN_COMBINACIONES") == []


class TestFrasesParaPareja:
    def test_pareja_existente(self):
        assert frases_para_pareja("POLITICA", "ECONOMIA") == [
            "política económica",
            "economía política",
        ]

    def test_pareja_inexistente(self):
        assert frases_para_pareja("ECONOMIA", "LENGUAJE") == []


class TestActualizarTermino:
    def test_agrega_chile_y_sufijo(self):
        with patch("topologia.web.compuestos.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 8, 2)
            assert (
                actualizar_termino("política económica")
                == "política económica Chile noticias agosto 2026"
            )

    def test_idempotente(self):
        with patch("topologia.web.compuestos.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 8, 2)
            termino = "economía Chile noticias agosto 2026"
            assert actualizar_termino(termino) == termino

    def test_con_chile_sin_sufijo(self):
        with patch("topologia.web.compuestos.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 8, 2)
            assert (
                actualizar_termino("economía Chile")
                == "economía Chile noticias agosto 2026"
            )
