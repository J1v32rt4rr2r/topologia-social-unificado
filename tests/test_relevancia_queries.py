from types import SimpleNamespace
from unittest.mock import patch

from topologia.models.schemas import EstrategiaRecoleccion
from topologia.web.relevancia import (
    _descripcion_nodo,
    _descripciones_dimensiones,
    _prompt_dimensiones,
    _queries_estaticas_dimensiones,
    _query_llm_aceptable,
    generar_queries,
    recolectar_por_queries,
)


class TestDimensiones:
    def test_descripciones_desde_yaml(self):
        descs = _descripciones_dimensiones("ECONOMIA")
        assert "Capacidad productiva" in descs["m"]
        assert "Ideología de mercado" in descs["l"]
        assert "Redes de producción" in descs["s"]

    def test_descripcion_nodo_une_dimensiones(self):
        texto = _descripcion_nodo("ECONOMIA")
        assert "Capacidad productiva" in texto
        assert "Ideología de mercado" in texto

    def test_fallback_para_nodo_desconocido(self):
        descs = _descripciones_dimensiones("NODO_INEXISTENTE")
        assert descs["l"] == "NODO_INEXISTENTE"

    def test_prompt_incluye_razon_logica(self):
        prompt = _prompt_dimensiones("SEXUALIDAD", None)
        assert "razón lógica" in prompt
        assert "material" in prompt
        assert "social" in prompt
        assert "Cosmovisión de la sexualidad" in prompt


class TestFiltroQueriesLLM:
    def _estrategia(self):
        return EstrategiaRecoleccion(
            nodos_prioritarios=["ECONOMIA", "TRABAJO"],
            nodos_con_brecha=["SEXUALIDAD"],
            queries_generadas={},
        )

    def test_rechaza_etiquetas_de_dimension(self):
        for basura in ["l", "m", "s", "material", "razón lógica", "razon logica", "social"]:
            assert not _query_llm_aceptable(basura), f"debió rechazar: {basura}"

    def test_acepta_query_real(self):
        assert _query_llm_aceptable("reforma del sistema de pensiones chileno")
        assert _query_llm_aceptable("debate constitucional 2026 en Chile")

    def test_rechaza_eco_de_instruccion(self):
        assert not _query_llm_aceptable("Busca cambios ideológicos en el debate priorizando la dimensión")

    @patch("topologia.web.relevancia.datetime")
    @patch("topologia.web.relevancia.LLMClient")
    def test_descarta_basura_y_usa_queries_validas(self, MockLLM, mock_dt):
        mock_dt.now.return_value = __import__("datetime").datetime(2026, 8, 2)
        instancia = MockLLM.return_value
        instancia.generar_json.return_value = [
            "l",
            "material",
            "razón lógica",
            "reforma del sistema de pensiones en Chile",
        ]
        queries = generar_queries(self._estrategia())
        for lista in queries.values():
            assert "l" not in lista
            assert "material" not in lista


class TestRecolectarMaxPorQuery:
    def _estrategia(self):
        return EstrategiaRecoleccion(
            nodos_prioritarios=["ECONOMIA", "TRABAJO"],
            nodos_con_brecha=["SEXUALIDAD"],
            queries_generadas={},
        )

    @patch("topologia.web.relevancia.buscar_ddg")
    def test_max_por_query_override(self, mock_buscar):
        from types import SimpleNamespace

        mock_buscar.side_effect = lambda *a, **k: [SimpleNamespace(id="x", nodo_sugerido=None)]
        datos = {
            "ECONOMIA": ["reforma de pensiones"],
            "TRABAJO": ["sueldo mínimo"],
        }
        recolectar_por_queries(datos, self._estrategia(), max_por_query=50)
        for call in mock_buscar.call_args_list:
            assert call.kwargs["max_resultados"] == 50


class TestQueriesEstaticas:
    @patch("topologia.web.relevancia.datetime")
    def test_una_query_por_dimension(self, mock_dt):
        mock_dt.now.return_value = __import__("datetime").datetime(2026, 8, 2)
        queries = _queries_estaticas_dimensiones("ECONOMIA")
        assert len(queries) == 3
        for q in queries:
            assert "Chile" in q
            assert "noticias agosto 2026" in q
        assert "Ideología de mercado" in queries[1]


class TestGenerarQueries:
    def _estrategia(self):
        return EstrategiaRecoleccion(
            nodos_prioritarios=["ECONOMIA", "TRABAJO"],
            nodos_con_brecha=["SEXUALIDAD"],
            dimensiones_inestables={"ECONOMIA": "l"},
            queries_generadas={},
        )

    @patch("topologia.web.relevancia.datetime")
    @patch("topologia.web.relevancia.LLMClient")
    def test_fallback_estatico_si_llm_falla(self, MockLLM, mock_dt):
        mock_dt.now.return_value = __import__("datetime").datetime(2026, 8, 2)
        instancia = MockLLM.return_value
        instancia.generar_json.side_effect = Exception("LLM caído")

        queries = generar_queries(self._estrategia())

        assert queries["ECONOMIA"]
        assert queries["TRABAJO"]
        assert queries["SEXUALIDAD"]
        assert "Ideología de mercado" in queries["ECONOMIA"][1]

    @patch("topologia.web.relevancia.datetime")
    @patch("topologia.web.relevancia.LLMClient")
    def test_fallback_estatico_si_llm_devuelve_vacio(self, MockLLM, mock_dt):
        mock_dt.now.return_value = __import__("datetime").datetime(2026, 8, 2)
        instancia = MockLLM.return_value
        instancia.generar_json.return_value = []

        queries = generar_queries(self._estrategia())
        assert "Ideología de mercado" in queries["ECONOMIA"][1]

    @patch("topologia.web.relevancia.LLMClient")
    def test_usa_queries_del_llm(self, MockLLM):
        instancia = MockLLM.return_value
        instancia.generar_json.side_effect = [
            ["debate por reforma educacional Chile", "universidades chilenas", "gratuidad educación"],
            ["inflación Chile agosto 2026"],
        ]

        queries = generar_queries(self._estrategia())
        assert queries["ECONOMIA"][0] == "inflación Chile agosto 2026"
        assert queries["SEXUALIDAD"][0] == "debate por reforma educacional Chile"

    @patch("topologia.web.relevancia.LLMClient")
    def test_prompt_menciona_dimensiones(self, MockLLM):
        instancia = MockLLM.return_value
        instancia.generar_json.return_value = ["query"]
        generar_queries(self._estrategia())

        prompts = [call.args[0] for call in instancia.generar_json.call_args_list]
        assert any("razón lógica" in p for p in prompts)
        assert any("dimensión 'l'" in p for p in prompts)

    @patch("topologia.web.relevancia.LLMClient")
    def test_prompt_menciona_combinaciones_de_nodos(self, MockLLM):
        instancia = MockLLM.return_value
        instancia.generar_json.return_value = ["query"]
        generar_queries(self._estrategia())

        prompts = [call.args[0] for call in instancia.generar_json.call_args_list]
        assert any("intersección" in p for p in prompts)
        assert any("educación sexual" in p for p in prompts)
        assert any("política religiosa" in p for p in prompts)

    @patch("topologia.web.relevancia.datetime")
    @patch("topologia.web.relevancia.LLMClient")
    def test_fallback_incluye_combinaciones_de_nodos(self, MockLLM, mock_dt):
        mock_dt.now.return_value = __import__("datetime").datetime(2026, 8, 2)
        instancia = MockLLM.return_value
        instancia.generar_json.side_effect = Exception("LLM caído")

        queries = generar_queries(self._estrategia())

        assert "política económica Chile noticias agosto 2026" in queries["ECONOMIA"]
        assert "educación sexual Chile noticias agosto 2026" in queries["SEXUALIDAD"]

    @patch("topologia.web.relevancia.buscar_ddg")
    def test_recolectar_por_queries_sufijo_idempotente(self, mock_buscar):
        mock_buscar.side_effect = [
            [SimpleNamespace(id="a1", nodo_sugerido=None)],
            [SimpleNamespace(id="a2", nodo_sugerido=None)],
        ]
        queries = {
            "ECONOMIA": ["inflación Chile noticias agosto 2026"],
            "TRABAJO": ["reforma laboral"],
        }

        items = recolectar_por_queries(queries, self._estrategia())

        llamadas = [call.args[0] for call in mock_buscar.call_args_list]
        assert llamadas[0] == "inflación Chile noticias agosto 2026"
        assert llamadas[1] == "reforma laboral Chile noticias agosto 2026"
        assert len(items) == 2
