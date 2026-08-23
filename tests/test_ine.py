from datetime import datetime
from unittest.mock import MagicMock, patch

import requests

from topologia.models.schemas import ItemInformativo
from topologia.web.ine import (
    _CACHE,
    _limpiar,
    _nodo_para,
    _parsear_agenda,
    _parsear_indicadores,
    _parsear_noticias,
    _parsear_periodo,
    obtener_items,
    obtener_items_agenda,
)

HTML_HOME = """
<div class="indicadorPrincipalHomeV3 indicadorPrincipalHomeV3-1">
    <a class="cuadroIndV3" href="/estadisticas-por-tema/precios-e-inflacion/indice-de-precios-al-consumidor">
        <h1>Índice de Precios al Consumidor</h1>
        <p class="cifraV3">0,0%</p>
        <p class="periodoCifraV3">Variación mensual. junio 2026</p>
    </a>
</div>
<div class="indicadorPrincipalHomeV3 indicadorPrincipalHomeV3-2">
    <a class="cuadroIndV3" href="/estadisticas-por-tema/mercado-laboral/ocupacion-y-desocupacion">
        <h1>Tasa de desocupación nacional</h1>
        <p class="cifraV3">9,4%</p>
        <p class="periodoCifraV3">Trimestre móvil<br>abril - junio 2026</p>
    </a>
</div>
<div class="indicadorPrincipalHomeV3 indicadorPrincipalHomeV3-3">
    <a class="cuadroIndV3" href="/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion">
        <h1>Población <br/> total</h1>
        <p class="cifraV3">20,2 mill</p>
        <p class="periodoCifraV3">Proyección (base Censo 2024) al 30 de junio de 2026</p>
    </a>
</div>
<div class="row noticiasHomeCont">
    <a href="http://www.ine.gob.cl/sala-de-prensa/noticia/1" class="contLinkNoticiaHome">
        <span class="noticiaHomeTitular">La tasa de desocupación nacional fue 9,4%</span>
        <span class="contendorFechaHome"><span class="fechaNoticia">31-07-2026</span></span>
    </a>
    <a href="http://www.ine.gob.cl/sala-de-prensa/noticia/2" class="contLinkNoticiaHome">
        <span class="noticiaHomeTitular">Denuncias registradas en 2025 aumentaron 4,6%</span>
        <span class="contendorFechaHome"><span class="fechaNoticia">30-07-2026</span></span>
    </a>
</div>
"""

HTML_AGENDA = """
<div class="cuadroMes">
    <h1 class="tituloMesEaV2"> agosto</h1>
    <div class="eventoAgendaV2">
        <span class="diaea2"><i class="fas fa-calendar-day"></i> 03 </span>
        <span class="horaea2"><i class="far fa-clock"></i> 09:00 </span>
        <span class="tituloea2">Transporte y Comunicaciones, período junio 2026</span>
    </div>
    <div class="eventoAgendaV2">
        <span class="diaea2"><i class="fas fa-calendar-day"></i> 07 </span>
        <span class="horaea2"><i class="far fa-clock"></i> 09:00 </span>
        <span class="tituloea2">Índice de Precios al Consumidor (IPC), período julio 2026</span>
    </div>
</div>
"""


class TestParsearPeriodo:
    def test_fecha_exacta(self):
        assert _parsear_periodo("Proyección al 30 de junio de 2026") == datetime(2026, 6, 30)

    def test_mes_y_anio(self):
        assert _parsear_periodo("Variación mensual. mayo 2026 (provisional)") == datetime(2026, 5, 31)

    def test_rango_de_meses(self):
        assert _parsear_periodo("Trimestre móvil abril - junio 2026") == datetime(2026, 6, 30)

    def test_sin_periodo_reconocible(self):
        assert _parsear_periodo("Dato no disponible") is None


class TestNodoPara:
    def test_demografia_sin_nodo(self):
        # Población/esperanza de vida no tienen nodo cultural directo: se
        # dejan sin nodo sugerido ("" ) para que la clasificación semántica
        # los asigne; "SOCIEDAD" no existe en la taxonomía.
        assert _nodo_para("Población total") == ""
        assert _nodo_para("Esperanza de vida al nacer") == ""
        assert _nodo_para("Denuncias registradas") == "POLITICA"

    def test_economia(self):
        assert _nodo_para("Índice de Precios al Consumidor") == "ECONOMIA"
        assert _nodo_para("Tasa de desocupación nacional") == "ECONOMIA"
        assert _nodo_para("Empleo Población Extranjera") == "ECONOMIA"
        assert _nodo_para("Informalidad Laboral") == "ECONOMIA"


class TestLimpiar:
    def test_quita_etiquetas_y_entidades(self):
        assert _limpiar("Poblaci&#243;n <br/> total") == "Población total"


class TestParseoHTML:
    def setup_method(self):
        _CACHE.clear()

    def test_parsear_indicadores(self):
        inds = _parsear_indicadores(HTML_HOME)
        assert len(inds) == 3
        assert inds[0]["valor"] == "0,0%"
        assert inds[0]["fecha"] == datetime(2026, 6, 30)
        assert inds[2]["titulo"] == "Población total"
        assert inds[2]["fecha"] == datetime(2026, 6, 30)

    def test_parsear_noticias(self):
        notas = _parsear_noticias(HTML_HOME)
        assert len(notas) == 2
        assert notas[0]["titulo"] == "La tasa de desocupación nacional fue 9,4%"
        assert notas[0]["fecha"] == datetime(2026, 7, 31)

    def test_parsear_agenda(self):
        with patch("topologia.web.ine.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 8, 2)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            eventos = _parsear_agenda(HTML_AGENDA)
        assert len(eventos) == 2
        assert eventos[0]["fecha"] == datetime(2026, 8, 3)
        assert eventos[1]["fecha"] == datetime(2026, 8, 7)

    @patch("topologia.web.ine.requests.get")
    def test_obtener_items_home(self, mock_get):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.apparent_encoding = "utf-8"
        resp.text = HTML_HOME
        mock_get.return_value = resp

        items = obtener_items(limite=15)
        assert len(items) == 5
        pob = [i for i in items if "Población total" in i.titulo][0]
        assert pob.nodo_sugerido == ""
        assert pob.fecha == datetime(2026, 6, 30)
        noticia = [i for i in items if i.titulo.startswith("La tasa de")][0]
        assert noticia.url == "http://www.ine.gob.cl/sala-de-prensa/noticia/1"

    @patch("topologia.web.ine.requests.get")
    def test_obtener_items_agenda(self, mock_get):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.apparent_encoding = "utf-8"
        resp.text = HTML_AGENDA
        mock_get.return_value = resp

        items = obtener_items_agenda(limite=10)
        assert len(items) == 2
        assert items[0].titulo.startswith("[Programado] Transporte")
        assert items[0].fecha == datetime(2026, 8, 3)
        assert "proxima_publicacion" in items[0].tags

    @patch("topologia.web.ine.requests.get")
    def test_error_de_red_devuelve_vacio(self, mock_get):
        mock_get.side_effect = requests.RequestException("red caída")
        assert obtener_items() == []
        assert obtener_items_agenda() == []

    def test_item_ine_directo(self):
        item = ItemInformativo(
            id="1", titulo="T", fuente="ine", contenido="c",
            fecha=datetime(2026, 8, 1),
        )
        assert item.fuente == "ine"
