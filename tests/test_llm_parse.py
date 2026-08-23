"""Tests del parseo robusto de JSON en LLMClient.generar_json."""

import pytest
from unittest.mock import patch

from topologia.models.llm import (
    LLMClient,
    _extraer_json,
    _parsear_json,
)


class TestExtraerJson:
    def test_bloque_markdown_json(self):
        assert _extraer_json('```json\n{"a": 1}\n```').startswith("{")

    def test_bloque_markdown_sin_lenguaje(self):
        assert _extraer_json('```\n{"a": 1}\n```').startswith("{")

    def test_quita_prosa_previa(self):
        texto = 'Aquí va el resultado:\n[{"a": 1}]'
        assert _extraer_json(texto).startswith("[")

    def test_texto_sin_json_se_mantiene(self):
        assert _extraer_json("no hay nada") == "no hay nada"


class TestParsearJson:
    def test_array_limpio(self):
        assert _parsear_json('[\n {"a": 1}\n]') == [{"a": 1}]

    def test_objeto_limpio(self):
        assert _parsear_json('{"a": 1}') == {"a": 1}

    def test_array_con_texto_sobrante(self):
        texto = (
            "[\n"
            ' {"patron_id": "P-001", "confianza": 0.5, "argumento": "a"},\n'
            ' {"patron_id": "P-002", "confianza": 0.6, "argumento": "b"}\n'
            "]  \nInterpretación: la caída del cobre resuena con el patrón."
        )
        res = _parsear_json(texto)
        assert isinstance(res, list)
        assert len(res) == 2
        assert res[0]["patron_id"] == "P-001"

    def test_prosa_previa_al_array(self):
        texto = (
            "Claro, estas son las especulaciones:\n"
            '[\n {"patron_id": "P-001", "confianza": 0.8, "argumento": "x"}\n]'
        )
        res = _parsear_json(texto)
        assert isinstance(res, list)
        assert res[0]["patron_id"] == "P-001"

    def test_bloque_markdown_con_objeto(self):
        assert _parsear_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_array_anidado_con_prosa(self):
        texto = (
            '{\n "items": [{"id": 1}, {"id": 2}],\n "total": 2\n}\n\n'
            "Resumen: proceso completado con éxito."
        )
        res = _parsear_json(texto)
        assert res == {"items": [{"id": 1}, {"id": 2}], "total": 2}

    def test_objetos_consecutivos_toma_el_primero(self):
        assert _parsear_json('{"a": 1} {"b": 2}') == {"a": 1}

    def test_sin_json_lanza_valueerror(self):
        with pytest.raises(ValueError):
            _parsear_json("el modelo respondió con texto plano sin JSON")


class TestGenerarJsonReintentos:
    @patch.object(LLMClient, "generar")
    def test_recupera_array_con_texto_sobrante(self, mock_generar):
        mock_generar.return_value = (
            '[\n {"patron_id": "P-001", "confianza": 0.8, "argumento": "x"},'
            ' {"patron_id": "P-002", "confianza": 0.7, "argumento": "y"}\n]'
            "\n  Observación final del modelo."
        )
        res = LLMClient().generar_json("prompt")
        assert isinstance(res, list)
        assert len(res) == 2
        assert mock_generar.call_count == 1

    @patch.object(LLMClient, "generar")
    def test_reintenta_y_recupera(self, mock_generar):
        mock_generar.side_effect = [
            "texto que no es JSON",
            '[{"patron_id": "P-001", "confianza": 0.8, "argumento": "x"}]',
        ]
        res = LLMClient().generar_json("prompt")
        assert isinstance(res, list)
        assert res[0]["patron_id"] == "P-001"
        assert mock_generar.call_count == 2

    @patch.object(LLMClient, "generar")
    def test_reintenta_respuesta_vacia(self, mock_generar):
        mock_generar.side_effect = [
            ValueError("respuesta vacía del LLM"),
            '{"ok": 1}',
        ]
        res = LLMClient().generar_json("prompt")
        assert res == {"ok": 1}
        assert mock_generar.call_count == 2

    @patch.object(LLMClient, "generar")
    def test_agota_reintentos(self, mock_generar):
        mock_generar.return_value = "sin JSON"
        with pytest.raises(ValueError):
            LLMClient().generar_json("prompt")
        assert mock_generar.call_count == 3