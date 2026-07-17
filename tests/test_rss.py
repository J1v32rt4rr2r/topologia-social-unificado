"""Tests del módulo RSS con dependencias externas mockeadas."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from topologia.web.rss import (
    _CACHE,
    _extraer_fecha,
    _fuente_real,
    _limpiar_html,
    obtener_items,
)


@pytest.fixture(autouse=True)
def limpiar_cache():
    _CACHE.clear()


class TestLimpiarHtml:
    def test_elimina_etiquetas(self):
        assert _limpiar_html("<p>Hola</p>") == "Hola"

    def test_entidades_html(self):
        assert _limpiar_html("&aacute; &ntilde;") == "á ñ"

    def test_espacios_multiples(self):
        assert _limpiar_html("a    b") == "a b"

    def test_texto_limpio(self):
        assert _limpiar_html("Hola mundo") == "Hola mundo"

    def test_vacio(self):
        assert _limpiar_html("") == ""


class TestExtraerFecha:
    def test_con_published_parsed(self):
        entry = {"published_parsed": (2024, 1, 15, 10, 30, 0, 0, 0, 0)}
        fecha = _extraer_fecha(entry)
        assert fecha.year == 2024
        assert fecha.month == 1
        assert fecha.day == 15

    def test_fecha_actual_sin_parsed(self):
        entry = {"title": "test"}
        fecha = _extraer_fecha(entry)
        assert fecha.tzinfo is not None


class TestFuenteReal:
    def test_con_source(self):
        entry = {"source": MagicMock(get=lambda x, **kw: "BioBioChile")}
        assert _fuente_real(entry, "http://example.com") == "BioBioChile"

    def test_sin_source(self):
        entry = {"title": "test"}
        assert _fuente_real(entry, "https://news.google.com/rss") == "news.google.com"


@patch("topologia.web.rss._cargar_config")
@patch("topologia.web.rss._fetch_rss")
class TestObtenerItems:
    def test_items_desde_rss(self, mock_fetch, mock_config):
        mock_config.return_value = {
            "rss": [{"url": "http://test.com/feed", "activo": True}]
        }
        mock_fetch.return_value = [
            MagicMock(id="rss-0", titulo="Noticia 1", fuente="test", contenido="...", url="http://a.com", fecha=datetime.now(timezone.utc), tags=["rss"]),
            MagicMock(id="rss-1", titulo="Noticia 2", fuente="test", contenido="...", url="http://b.com", fecha=datetime.now(timezone.utc), tags=["rss"]),
        ]
        items = obtener_items(limite=10, usar_cache=False)
        assert len(items) == 2

    def test_sin_feeds_activos(self, mock_fetch, mock_config):
        mock_config.return_value = {"rss": []}
        items = obtener_items(limite=10, usar_cache=False)
        assert len(items) == 0

    def test_cache(self, mock_fetch, mock_config):
        mock_config.return_value = {
            "rss": [{"url": "http://test.com/feed", "activo": True}]
        }
        mock_fetch.return_value = [
            MagicMock(id="rss-0", titulo="N", fuente="t", contenido=".", url="http://a.com", fecha=datetime.now(timezone.utc), tags=["rss"]),
        ]
        obtener_items(limite=10, usar_cache=False)
        items2 = obtener_items(limite=10, usar_cache=True)
        assert len(items2) == 1
        assert mock_fetch.call_count == 1

    def test_diferentes_limites_no_comparten_cache(self, mock_fetch, mock_config):
        mock_config.return_value = {
            "rss": [{"url": "http://test.com/feed", "activo": True}]
        }
        mock_fetch.return_value = [
            MagicMock(id="rss-0", titulo="N", fuente="t", contenido=".", url="http://a.com", fecha=datetime.now(timezone.utc), tags=["rss"]),
        ]
        obtener_items(limite=5, usar_cache=False)
        obtener_items(limite=10, usar_cache=False)
        assert mock_fetch.call_count == 2
