"""Tests del módulo BCentral (Banco Central de Chile) y filtros de actualidad."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import requests

from topologia.agents.base import Agent, _fecha_item
from topologia.models.schemas import ConfigAgente, ItemInformativo
from topologia.web.bcentral import (
    _CACHE,
    _consultar_serie_bde,
    _es_valor_valido,
    _parsear_fecha_selector,
    obtener_items,
    obtener_items_bde,
    obtener_items_bde_periodicos,
)
from topologia.web.scraping import _termino_actualizado
from topologia.web.search import _DOMINIOS_REFERENCIA, buscar

HTML_EJEMPLO = """<html><body>
<input name="txtDate" type="text" id="txtDate" value="04 Ago 2026" />
<label id="lblSerie1_1">Unidad de fomento (UF)</label>
<label id="lblValor1_1">40.844,79</label>
<label id="lblSerie1_2">Indice de valor promedio (IVP)</label>
<label id="lblValor1_2">42.207,78</label>
<label id="lblSerie1_3">Dólar observado</label>
<label id="lblValor1_3">ND</label>
<label id="lblSerie2_5">Libra de Cobre</label>
<label id="lblValor2_5">3,65</label>
<label id="lblSerie2_9">Otras paridades</label>
<label id="lblValor2_9">&nbsp;</label>
</body></html>"""


class TestBCentral:
    def setup_method(self):
        _CACHE.clear()

    @patch("topologia.web.bcentral.requests.get")
    def test_parsea_indicadores_y_salta_nd(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.text = HTML_EJEMPLO
        mock_get.return_value = resp

        items = obtener_items()
        assert len(items) == 3
        assert items[0].titulo.startswith("Unidad de fomento")
        assert items[1].titulo.startswith("Indice de valor promedio")
        assert items[2].titulo == "Libra de Cobre: 3,65"
        assert all(i.nodo_sugerido == "ECONOMIA" for i in items)
        assert all(i.fecha == datetime(2026, 8, 4, tzinfo=timezone.utc) for i in items)

    def test_fecha_selector_espanol(self):
        assert _parsear_fecha_selector("04 Ago 2026") == datetime(2026, 8, 4, tzinfo=timezone.utc)
        assert _parsear_fecha_selector("10 Sept 2025") == datetime(2025, 9, 10, tzinfo=timezone.utc)
        assert _parsear_fecha_selector("fecha invalida") is None

    def test_valor_valido(self):
        assert not _es_valor_valido("ND")
        assert not _es_valor_valido("&nbsp;")
        assert not _es_valor_valido("")
        assert _es_valor_valido("40.844,79")
        assert _es_valor_valido("3,65")

    @patch("topologia.web.bcentral.requests.get")
    def test_error_de_red_devuelve_vacio(self, mock_get):
        mock_get.side_effect = requests.RequestException("red caída")
        assert obtener_items() == []


class TestBDE:
    def setup_method(self):
        _CACHE.clear()

    @patch("topologia.web.bcentral.os")
    def test_sin_token_no_consulta(self, mock_os):
        mock_os.getenv.return_value = ""
        assert obtener_items_bde() == []

    @patch("topologia.web.bcentral.requests.get")
    @patch("topologia.web.bcentral.os")
    def test_consulta_series_con_token(self, mock_os, mock_get):
        mock_os.getenv.return_value = "token-prueba"
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.content = b'{"Codigo": 0, "Series": {"seriesId": "F073.TCO.PRE.Z.D", "Obs": [{"indexDateString": "01-08-2026", "value": "925.0", "statusCode": "OK"}, {"indexDateString": "02-08-2026", "value": "927.5", "statusCode": "OK"}]}, "SeriesInfos": []}'
        mock_get.return_value = resp

        items = obtener_items_bde()
        assert len(items) == 5
        dol = [i for i in items if i.titulo.startswith("Dólar observado")][0]
        assert dol.titulo == "Dólar observado: 927.50"
        assert dol.fecha == datetime(2026, 8, 2)
        assert dol.fuente == "bcentral-bde"

    @patch("topologia.web.bcentral.requests.get")
    @patch("topologia.web.bcentral.os")
    def test_salta_fines_de_semana_nd(self, mock_os, mock_get):
        mock_os.getenv.return_value = "token-prueba"
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.content = b'{"Codigo": 0, "Series": {"Obs": [{"indexDateString": "01-08-2026", "value": "NaN", "statusCode": "ND"}, {"indexDateString": "02-08-2026", "value": "NaN", "statusCode": "ND"}, {"indexDateString": "03-08-2026", "value": "928.42", "statusCode": "OK"}]}, "SeriesInfos": []}'
        mock_get.return_value = resp

        puntos = _consultar_serie_bde("F073.TCO.PRE.Z.D")
        assert puntos is not None
        assert len(puntos) == 1
        assert puntos[0] == (datetime(2026, 8, 3), "928.42")

    @patch("topologia.web.bcentral.requests.get")
    @patch("topologia.web.bcentral.os")
    def test_serie_invalida_se_omite(self, mock_os, mock_get):
        mock_os.getenv.return_value = "token-prueba"
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.content = b'{"Codigo": -5, "Descripcion": "Invalid username or password", "Series": null, "SeriesInfos": []}'
        mock_get.return_value = resp
        assert _consultar_serie_bde("F073.TCO.PRE.Z.D") is None
        assert obtener_items_bde() == []

    @patch("topologia.web.bcentral.requests.get")
    @patch("topologia.web.bcentral.os")
    def test_series_periodicas_contexto(self, mock_os, mock_get):
        mock_os.getenv.return_value = "token-prueba"
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.content = b'{"Codigo": 0, "Series": {"Obs": [{"indexDateString": "01-06-2026", "value": "112.34", "statusCode": "OK"}]}, "SeriesInfos": []}'
        mock_get.return_value = resp

        items = obtener_items_bde_periodicos()
        assert len(items) == 3
        imacec = [i for i in items if i.titulo.startswith("IMACEC")][0]
        assert imacec.fuente == "bcentral-bde-periodica"
        assert imacec.fecha == datetime(2026, 6, 1)
        assert "contexto" in imacec.tags


class TestBuscarFiltro:
    @patch("ddgs.DDGS")
    def test_excluye_dominios_de_referencia(self, MockDDGS):
        instancia = MockDDGS.return_value.__enter__.return_value
        instancia.text.return_value = [
            {"title": "Noticia economía Chile", "body": "mercado chileno", "href": "https://www.biobiochile.cl/a"},
            {"title": "Economía de Chile", "body": "la economía de Chile", "href": "https://es.wikipedia.org/wiki/Economia_de_Chile"},
            {"title": "Chile en la memoria", "body": "archivo", "href": "https://www.memoriachilena.gob.cl/archivo"},
        ]
        items = buscar("economía Chile", max_resultados=10)
        assert len(items) == 1
        assert items[0].url == "https://www.biobiochile.cl/a"
        assert "sin_fecha" in items[0].tags

    def test_dominios_referencia_definidos(self):
        assert "wikipedia.org" in _DOMINIOS_REFERENCIA


class TestFormatearItems:
    def setup_method(self):
        self.agent = Agent(ConfigAgente(nombre="Test", prompt=""))

    def test_muestra_fecha_por_item(self):
        item = ItemInformativo(
            id="1", titulo="Titular", fuente="rss",
            contenido="cuerpo", fecha=datetime(2026, 8, 2),
        )
        texto = self.agent.formatear_items([item])
        assert "Fecha: 02/08/2026" in texto

    def test_sin_fecha_etiquetado(self):
        item = ItemInformativo(
            id="1", titulo="Titular", fuente="duckduckgo",
            contenido="cuerpo", tags=["sin_fecha"],
        )
        assert _fecha_item(item) == "no disponible"
        assert "Fecha: no disponible" in self.agent.formatear_items([item])


class TestTerminoActualizado:
    def test_agrega_mes_y_anio(self):
        with patch("topologia.web.compuestos.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 8, 2)
            resultado = _termino_actualizado("economía Chile")
            assert resultado == "economía Chile noticias agosto 2026"
