"""Tests del pipeline analógico (engine)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from topologia.pipeline.engine import Pipeline, ResultadoPipeline


class TestResultadoPipeline:
    def test_resumen_basico(self):
        r = ResultadoPipeline(texto="test", nombre_texto="test")
        assert "Pipeline: test" in r.resumen()

    def test_resumen_con_fase1(self):
        r = ResultadoPipeline(texto="a", nombre_texto="a", fase1={"estructura_superficial": {"genero": "poema"}})
        assert "F1: estructura=poema" in r.resumen()

    def test_resumen_con_error(self):
        r = ResultadoPipeline(texto="a", nombre_texto="a", error="Algo falló")
        assert "ERROR: Algo falló" in r.resumen()

    def test_resumen_fase6(self):
        r = ResultadoPipeline(texto="a", nombre_texto="a",
            fase6={"reglas_formales": [{"r": "1"}], "axiomas": [{"a": "1"}]})
        assert "F6: 1 reglas, 1 axiomas" in r.resumen()


class TestPipelineEjecutar:
    @patch("topologia.pipeline.engine.Pipeline._fase1_inmersion")
    @patch("topologia.pipeline.engine.Pipeline._fase2_pictorica")
    @patch("topologia.pipeline.engine.Pipeline._fase3_analisis")
    @patch("topologia.pipeline.engine.Pipeline._fase4_reescritura")
    @patch("topologia.pipeline.engine.Pipeline._fase5_emergencias")
    @patch("topologia.pipeline.engine.Pipeline._fase6_formalizacion")
    @patch("topologia.pipeline.engine.Pipeline._guardar_resultado")
    @patch("topologia.pipeline.engine.Pipeline._cargar_config")
    def test_ejecutar_todas_las_fases(self, mock_config, mock_guardar, mock_f6, mock_f5, mock_f4, mock_f3, mock_f2, mock_f1):
        pipe = Pipeline()
        mock_config.return_value = {}
        mock_f1.return_value = {"ok": True}
        mock_f2.return_value = {"ok": True}
        mock_f3.return_value = {"ok": True}
        mock_f4.return_value = {"ok": True}
        mock_f5.return_value = {"ok": True}
        mock_f6.return_value = {"ok": True}

        import os, tempfile
        fd, path = tempfile.mkstemp(suffix=".txt", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("contenido de prueba")
            result = pipe.ejecutar(path)
        finally:
            Path(path).unlink(missing_ok=True)

        assert result.error is None
        assert result.fase1 == {"ok": True}
        assert result.fase2 == {"ok": True}
        assert result.fase3 == {"ok": True}
        assert result.fase4 == {"ok": True}
        assert result.fase5 == {"ok": True}
        assert result.fase6 == {"ok": True}
        mock_guardar.assert_called_once()

    def test_archivo_no_encontrado(self):
        pipe = Pipeline()
        result = pipe.ejecutar("/no/existe.txt")
        assert result.error is not None
        assert "no encontrado" in result.error

    @patch("topologia.pipeline.engine.Pipeline._fase1_inmersion")
    def test_error_en_fase_manejado(self, mock_f1):
        pipe = Pipeline()
        mock_f1.side_effect = ValueError("error simulado")

        import os, tempfile
        fd, path = tempfile.mkstemp(suffix=".txt", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("test")
            result = pipe.ejecutar(path)
        finally:
            Path(path).unlink(missing_ok=True)

        assert result.error is not None
        assert "error simulado" in result.error


class TestFormatearDecisiones:
    @patch("topologia.memoria.decisiones.DecisionDB.listar")
    def test_sin_decisiones(self, mock_listar):
        mock_listar.return_value = []
        pipe = Pipeline()
        resultado = pipe._formatear_decisiones_para_prompt()
        assert resultado == "No hay decisiones previas."

    @patch("topologia.memoria.decisiones.DecisionDB.listar")
    def test_con_decisiones(self, mock_listar):
        mock_listar.return_value = [
            {"id": "dec-001", "tipo": "lesson", "contenido": "aprendizaje importante"},
        ]
        pipe = Pipeline()
        resultado = pipe._formatear_decisiones_para_prompt()
        assert "dec-001" in resultado
        assert "lesson" in resultado
