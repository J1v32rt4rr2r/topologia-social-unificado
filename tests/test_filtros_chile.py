"""Tests de los filtros de relevancia chilena y de ruido internacional."""

from topologia.models.schemas import EstrategiaRecoleccion, ItemInformativo
from topologia.web.relevancia import puntuar_relevancia
from topologia.web.rss import filtrar_relevancia_chile


def _item(titulo, fuente="feeds.elpais.com", contenido=""):
    return ItemInformativo(
        id="t-001",
        titulo=titulo,
        fuente=fuente,
        contenido=contenido,
        url="https://ejemplo.cl/a",
    )


_ESTRATEGIA = EstrategiaRecoleccion()


class TestFiltroChileRSS:
    def test_titulo_internacional_con_congreso_se_descarta(self):
        it = _item(
            "JoAnna Mendoza, candidata demócrata al Congreso por Arizona: "
            "Los indocumentados merecen un camino hacia la ciudadanía",
            fuente="feeds.elpais.com",
        )
        assert filtrar_relevancia_chile([it]) == []

    def test_titulo_con_token_fuerte_chileno_se_conserva(self):
        it = _item(
            "La economía chilena repunta y evita la caída del tipo de cambio",
            fuente="feeds.elpais.com",
        )
        assert len(filtrar_relevancia_chile([it])) == 1

    def test_fuente_chilena_pasa_por_origen(self):
        it = _item("Mesa de trabajo en La Moneda por seguridad", fuente="cambio21.cl")
        assert len(filtrar_relevancia_chile([it])) == 1

    def test_fuente_chilena_descubierta_pasa_por_origen(self):
        it = _item("Finaliza TEPP en Cañete: estudiantes protagonistas", fuente="www.educacion2020.cl")
        assert len(filtrar_relevancia_chile([it])) == 1


class TestPuntuarRelevancia:
    def test_noticia_iran_se_descarta(self):
        it = _item(
            "Irán lanza ataques contra Israel y la Casa Blanca condena la escalada",
            fuente="cambio21.cl",
        )
        assert puntuar_relevancia([it], _ESTRATEGIA) == []

    def test_elecciones_eeuu_se_descartan(self):
        it = _item(
            "Harris y Trump miden fuerzas de cara a las presidenciales en estados unidos",
            fuente="www.elciudadano.com",
        )
        assert puntuar_relevancia([it], _ESTRATEGIA) == []

    def test_candidata_arizona_fuente_no_chilena_se_descarta(self):
        it = _item(
            "JoAnna Mendoza, candidata demócrata al Congreso por Arizona: "
            "Los indocumentados merecen un camino hacia la ciudadanía",
            fuente="feeds.elpais.com",
        )
        assert puntuar_relevancia([it], _ESTRATEGIA) == []

    def test_fuente_no_chilena_con_senal_chilena_se_conserva(self):
        it = _item(
            "Reforma previsional avanza en su tercer trámite",
            fuente="feeds.elpais.com",
            contenido="La Cámara de Diputados de Chile aprobó la reforma previsional.",
        )
        res = puntuar_relevancia([it], _ESTRATEGIA)
        assert len(res) == 1
        assert res[0].score_relevancia >= 0.5

    def test_noticia_chilena_local_se_conserva(self):
        it = _item(
            "Boric felicita a Diputada Gael Yeomans tras ganar elecciones del Frente Amplio",
            fuente="cambio21.cl",
        )
        assert len(puntuar_relevancia([it], _ESTRATEGIA)) == 1

    def test_partido_republicano_chileno_no_se_descarta(self):
        it = _item(
            "Partido Republicano de Kast propone privatizar Codelco y Correos de Chile",
            fuente="resumen.cl",
        )
        assert len(puntuar_relevancia([it], _ESTRATEGIA)) == 1