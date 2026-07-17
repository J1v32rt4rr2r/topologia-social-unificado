"""Tests de agentes con LLM mockeado."""

from datetime import datetime
from unittest.mock import patch

from topologia.agents.artista import Artista
from topologia.agents.estadista import Estadista
from topologia.agents.filosofo import Filosofo
from topologia.agents.sociologo import Sociologo
from topologia.agents.redactor import Redactor
from topologia.models.schemas import (
    EstadoCultural, EvaluacionNodo, ItemInformativo,
    Estudio, Especulacion, OperacionCinetica,
)


MOCK_JSON_RESPONSE = '{"puntuacion": 7.5, "justificacion": "test", "tendencia": "mejora", "senal_temprana": ""}'


def _mock_generar_json(*args, **kwargs):
    return {"puntuacion": 7.5, "justificacion": "test", "tendencia": "mejora", "senal_temprana": ""}


def _mock_item(id_suffix="001") -> ItemInformativo:
    return ItemInformativo(
        id=f"test-{id_suffix}",
        titulo="Test title",
        fuente="test",
        contenido="Test content",
        url="https://test.cl",
        fecha=datetime.now(),
    )


@patch("topologia.agents.base.Agent.ejecutar_prompt", return_value=_mock_generar_json())
def test_estadista_evaluar(mock_llm):
    ag = Estadista()
    items = [_mock_item()]
    result = ag.evaluar_nodo("ECONOMIA", items)
    assert result.nodo_id == "ECONOMIA"
    assert result.dimension_m == 7.5
    assert result.tendencia_m == "mejora"


@patch("topologia.agents.base.Agent.ejecutar_prompt", return_value=_mock_generar_json())
def test_filosofo_evaluar(mock_llm):
    ag = Filosofo()
    items = [_mock_item()]
    result = ag.evaluar_nodo("POLITICA", items)
    assert result.nodo_id == "POLITICA"
    assert result.dimension_l == 7.5


@patch("topologia.agents.base.Agent.ejecutar_prompt", return_value=_mock_generar_json())
def test_sociologo_evaluar(mock_llm):
    ag = Sociologo()
    items = [_mock_item()]
    result = ag.evaluar_nodo("TRABAJO", items)
    assert result.nodo_id == "TRABAJO"
    assert result.dimension_s == 7.5


@patch("topologia.agents.artista.Artista.ejecutar_prompt")
def test_artista_especular(mock_llm):
    mock_llm.return_value = [{
        "patron_id": "P-015",
        "items": ["item_001"],
        "confianza": 0.85,
        "argumento": "test argumento",
        "nodos_sugeridos": ["ECONOMIA"],
        "pregunta_abierta": "¿test?",
    }]
    ag = Artista()
    items = [_mock_item()]
    result = ag.especular(items)
    assert len(result) == 1
    assert result[0].patron_id == "P-015"
    assert result[0].confianza == 0.85


@patch("topologia.agents.redactor.Redactor.ejecutar_prompt")
def test_redactor_sintetizar(mock_llm):
    mock_llm.return_value = {
        "panorama": "test panorama",
        "dinamicas": "test dinamicas",
        "especulaciones_y_estudios": "test esp",
        "alertas": [],
        "mirada_adelante": "test",
        "resumen_ejecutivo": "test resumen",
        "dashboard": {
            "metrica_principal": "δ = 30°",
            "cambio_clave": "test",
            "nodos_criticos": [],
            "patrones_nuevos": [],
        },
    }
    ag = Redactor()
    estado = EstadoCultural(
        sociedad="Chile",
        M_m=3.0, M_l=5.0, M_s=4.0,
        delta_promedio=30.0,
        nodos=[EvaluacionNodo(
            nodo_id="TEST", nodo_nombre="Test",
            dimension_m=3.0, dimension_l=5.0, dimension_s=4.0,
        )],
    )
    ops = [OperacionCinetica(codigo="O1a", nombre="Test", intensidad=0.5)]
    esp = [Especulacion(patron_id="P-001", confianza=0.5, argumento="test")]
    estudios = [Estudio(especulacion_id="ESP-001", patron_id="P-001")]

    result = ag.sintetizar(estado, ops, esp, estudios)
    assert result.panorama == "test panorama"
    assert result.resumen_ejecutivo == "test resumen"


@patch("topologia.agents.artista.Artista.ejecutar_prompt")
def test_artista_especular_sin_resultados(mock_llm):
    mock_llm.return_value = []
    ag = Artista()
    result = ag.especular([_mock_item()])
    assert result == []


@patch("topologia.agents.base.Agent.ejecutar_prompt")
def test_estadista_validar(mock_llm):
    mock_llm.return_value = {
        "dimension": "M_m", "patron_id": "P-015",
        "confirmado": True, "confianza": 0.8,
        "evidencia": "test", "contraevidencia": "",
        "conclusion": "confirmado",
    }
    ag = Estadista()
    items = [_mock_item()]
    result = ag.validar_estudio(items,
        patron_id="P-015",
        forma_patron="Caída vertical",
        significado_patron="test",
        items_originales="item_001",
        argumento_artista="test",
        confianza_artista="0.8",
    )
    assert result.dimension == "M_m"
    assert result.confianza == 0.8
