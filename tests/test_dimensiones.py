from unittest.mock import patch

from topologia.models.schemas import ItemInformativo
from topologia.web.dimensiones import (
    cobertura_por_dimension,
    dimensiones_ciegas,
    nodos_validos,
    query_para_dimension,
    queries_para_ciegas,
    releer_ciegas,
    _nivel_heuristica,
)


def _item(texto, nodo=""):
    return ItemInformativo(
        id=texto[:6], titulo=texto, fuente="x", contenido="", nodo_sugerido=nodo
    )


class TestNodos:
    def test_nueve_nodos_desde_yaml(self):
        nodos = nodos_validos()
        assert len(nodos) == 9
        assert "ECONOMIA" in nodos


class TestNivelHeuristica:
    def test_razon_logica_por_ideologia(self):
        resultado = _nivel_heuristica("La ideologia de mercado y la teoria del valor")
        assert resultado == ("ECONOMIA", "l")

    def test_social_por_sindicatos(self):
        resultado = _nivel_heuristica("Los sindicatos organizan la division social del trabajo")
        assert resultado == ("TRABAJO", "s")

    def test_sin_coincidencias_devuelve_none(self):
        assert _nivel_heuristica("zxqw vbnm qwerty asdfg") is None


class TestCascada:
    @patch("topologia.web.dimensiones._nivel_llm_deepseek", return_value=None)
    @patch("topologia.web.dimensiones._nivel_llm_local", return_value=None)
    @patch("topologia.web.dimensiones._nivel_embeddings")
    def test_prefiere_heuristica_antes_que_llm(self, mock_emb, mock_llm, mock_maestro):
        # heurística no dispara → sigue a embeddings y LLM; si todo falla → maestro
        mock_emb.return_value = None
        from topologia.web.dimensiones import clasificar_dimension

        r = clasificar_dimension(_item("hablando de nada en absoluto con terminos raros"))
        assert r is None
        assert mock_emb.called
        assert mock_llm.called
        assert mock_maestro.called

    @patch("topologia.web.dimensiones._nivel_llm_deepseek", return_value=("LENGUAJE", "l"))
    @patch("topologia.web.dimensiones._nivel_llm_local", return_value=None)
    @patch("topologia.web.dimensiones._nivel_embeddings", return_value=None)
    def test_maestro_llena_hueco_cuando_local_falla(self, mock_emb, mock_llm, mock_maestro):
        from topologia.web.dimensiones import clasificar_dimension

        item = _item("hablando de nada en absoluto con terminos raros")
        r = clasificar_dimension(item)
        assert r == ("LENGUAJE", "l")
        assert item.dimension_sugerida == "l"


class TestCobertura:
    def test_cobertura_27_con_ceros_default(self):
        items = []
        cobertura = cobertura_por_dimension(items)
        assert len(cobertura) == 9
        for dims in cobertura.values():
            assert len(dims) == 3

    def test_cuenta_items_por_coordenada(self):
        items_por_dato = [
            _item("Ideologia de mercado", "ECONOMIA"),
            _item("Redes de produccion", "ECONOMIA"),
            _item("Leyes y constitucion", "POLITICA"),
        ]
        for it in items_por_dato:
            it.dimension_sugerida = "l" if "Ideologia" in it.titulo else ("s" if "Redes" in it.titulo else "l")
        cobertura = cobertura_por_dimension(items_por_dato)
        assert cobertura["ECONOMIA"]["l"] == 1
        assert cobertura["ECONOMIA"]["s"] == 1
        assert cobertura["POLITICA"]["l"] == 1

    def test_dimensiones_ciegas(self):
        cobertura = {
            "ECONOMIA": {"m": 1, "l": 0, "s": 1},
            "POLITICA": {"m": 0, "l": 0, "s": 0},
        }
        ciegas = dimensiones_ciegas(cobertura)
        assert ciegas["ECONOMIA"] == ["l"]
        assert ciegas["POLITICA"] == ["m", "l", "s"]


class TestQueriesRedestilacion:
    def test_query_para_dimension_con_actualidad(self):
        q = query_para_dimension("POLITICA", "l")
        assert "Chile" in q
        assert "noticias" in q
        assert q.startswith("Filosofía política")

    def test_query_para_dimension_desconocida(self):
        q = query_para_dimension("NODO_RARO", "x")
        assert "Chile" in q

    def test_queries_para_ciegas_mapea_nodo_y_dim(self):
        resultado = queries_para_ciegas({"ECONOMIA": ["l"], "POLITICA": ["m", "s"]})
        assert set(resultado) == {"ECONOMIA", "POLITICA"}
        assert len(resultado["POLITICA"]) == 2
        assert all("Chile" in s for s in resultado["ECONOMIA"])


class TestReleerCiegas:
    def _item(self, texto, nodo, dim):
        return ItemInformativo(
            id=texto[:6], titulo=texto, fuente="x", contenido="", nodo_sugerido=nodo,
            dimension_sugerida=dim,
        )

    def test_rellena_coordenada_ciega_desde_coordenada_redundante(self):
        it1 = self._item("Debate ideologico de mercado", "ECONOMIA", "l")
        it2 = self._item("El parlamento aprueba la constitucion", "ECONOMIA", "l")
        items = [it1, it2]
        cobertura = {"ECONOMIA": {"m": 0, "l": 2, "s": 0}}
        ciegas = {"ECONOMIA": ["m"]}
        with patch(
            "topologia.web.dimensiones._nivel_llm_local",
            side_effect=[("ECONOMIA", "m")],
        ):
            rellenas = releer_ciegas(items, ciegas, cobertura)
        assert rellenas == 1
        assert it1.dimension_sugerida == "m"

    def test_respeta_unico_ocupante_de_otra_coordenada(self):
        it1 = self._item("El parlamento aprueba la constitucion", "ECONOMIA", "s")
        items = [it1]
        cobertura = {"ECONOMIA": {"m": 0, "l": 0, "s": 1}}
        ciegas = {"ECONOMIA": ["m"]}
        with patch(
            "topologia.web.dimensiones._nivel_llm_local",
            side_effect=[("ECONOMIA", "m")],
        ):
            rellenas = releer_ciegas(items, ciegas, cobertura)
        assert rellenas == 0
        assert it1.dimension_sugerida == "s"

    def test_no_reetiqueta_sin_items_del_nodo(self):
        items = [self._item("Solo politica", "POLITICA", "m")]
        ciegas = {"RELIGION": ["m", "l", "s"]}
        cobertura = {"RELIGION": {"m": 0, "l": 0, "s": 0}}
        with patch("topologia.web.dimensiones._nivel_llm_local") as llm:
            rellenas = releer_ciegas(items, ciegas, cobertura)
        assert rellenas == 0
        llm.assert_not_called()