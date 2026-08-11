from types import SimpleNamespace
from unittest.mock import patch

from topologia.web.scraping import recolectar_para_nodo


class TestRecolectarConCombinaciones:
    @patch("topologia.web.scraping.buscar")
    def test_incluye_frases_compuestas_desde_config(self, mock_buscar):
        mock_buscar.return_value = []
        terminos_vistos: list[str] = []

        def capturar(termino, max_resultados):
            terminos_vistos.append(termino)
            return []

        mock_buscar.side_effect = capturar

        recolectar_para_nodo("POLITICA", max_items=5)

        assert any(t.startswith("política económica Chile") for t in terminos_vistos)
        assert any(t.startswith("política religiosa Chile") for t in terminos_vistos)
        assert terminos_vistos[0].endswith("noticias agosto 2026")

    @patch("topologia.web.scraping.buscar")
    def test_compuestos_pueden_llenar_items(self, mock_buscar):
        items = [
            SimpleNamespace(
                id=f"r{i}",
                url=f"https://ejemplo.cl/{i}",
                titulo="",
                contenido="",
                fuente="",
                nodo_sugerido=None,
            )
            for i in range(3)
        ]
        mock_buscar.return_value = items

        resultado = recolectar_para_nodo("SEXUALIDAD", max_items=3)

        assert len(resultado) == 3
        assert all(i.nodo_sugerido == "SEXUALIDAD" for i in resultado)
