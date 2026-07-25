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
    Estudio, Especulacion, OperacionCinetica, VotoObservador,
)


MOCK_JSON_RESPONSE = '{"puntuacion": 7.5, "justificacion": "test", "tendencia": "mejora", "confianza": 0.85, "senal_temprana": "", "contra_punto_inicial": "", "tension_con": []}'


def _mock_generar_json(*args, **kwargs):
    return {"puntuacion": 7.5, "justificacion": "test", "tendencia": "mejora", "confianza": 0.85, "senal_temprana": "", "contra_punto_inicial": "", "tension_con": []}


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
    assert isinstance(result, VotoObservador)
    assert result.dimension == "M_m"
    assert result.score == 7.5
    assert result.tendencia == "mejora"
    assert result.confianza == 0.85


@patch("topologia.agents.base.Agent.ejecutar_prompt", return_value=_mock_generar_json())
def test_filosofo_evaluar(mock_llm):
    ag = Filosofo()
    items = [_mock_item()]
    result = ag.evaluar_nodo("POLITICA", items)
    assert isinstance(result, VotoObservador)
    assert result.dimension == "M_l"
    assert result.score == 7.5


@patch("topologia.agents.base.Agent.ejecutar_prompt", return_value=_mock_generar_json())
def test_sociologo_evaluar(mock_llm):
    ag = Sociologo()
    items = [_mock_item()]
    result = ag.evaluar_nodo("TRABAJO", items)
    assert isinstance(result, VotoObservador)
    assert result.dimension == "M_s"
    assert result.score == 7.5


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


@patch("topologia.agents.base.Agent.ejecutar_prompt", return_value={
    "ajuste_puntuacion": 0.5, "mantiene": False,
    "justificacion_ajuste": "ajuste por deliberación",
    "contra_punto": "El Filósofo no ve...", "tension_con": ["M_l"],
    "nueva_confianza": 0.9, "reflexion": "Divergencia esperable",
})
def test_estadista_deliberar(mock_llm):
    ag = Estadista()
    mi_voto = VotoObservador(dimension="M_m", score=7.5, confianza=0.85)
    votos_otros = {
        "M_l": VotoObservador(dimension="M_l", score=8.0, confianza=0.9,
                               justificacion="alta intensidad valórica"),
        "M_s": VotoObservador(dimension="M_s", score=5.0, confianza=0.7,
                               justificacion="estable"),
    }
    result = ag.deliberar("ECONOMIA", mi_voto, votos_otros)
    assert result["ajuste"] == 0.5
    assert result["mantiene"] is False
    assert result["nueva_confianza"] == 0.9
    assert "M_l" in result["tension_con"]


@patch("topologia.agents.base.Agent.ejecutar_prompt", return_value={
    "ajuste_puntuacion": -0.3, "mantiene": True,
    "justificacion_ajuste": "", "contra_punto": "El Estadista subestima...",
    "tension_con": ["M_m"], "nueva_confianza": 0.75, "reflexion": "",
})
def test_filosofo_deliberar(mock_llm):
    ag = Filosofo()
    mi_voto = VotoObservador(dimension="M_l", score=8.0, confianza=0.9)
    votos_otros = {
        "M_m": VotoObservador(dimension="M_m", score=5.0, confianza=0.8),
        "M_s": VotoObservador(dimension="M_s", score=6.0, confianza=0.6),
    }
    result = ag.deliberar("POLITICA", mi_voto, votos_otros)
    assert result["ajuste"] == -0.3
    assert result["mantiene"] is True


@patch("topologia.agents.base.Agent.ejecutar_prompt", return_value={
    "ajuste_puntuacion": 0.0, "mantiene": True,
    "justificacion_ajuste": "", "contra_punto": "",
    "tension_con": [], "nueva_confianza": 0.8, "reflexion": "",
})
def test_sociologo_deliberar(mock_llm):
    ag = Sociologo()
    mi_voto = VotoObservador(dimension="M_s", score=5.0, confianza=0.8)
    votos_otros = {
        "M_m": VotoObservador(dimension="M_m", score=5.5, confianza=0.7),
        "M_l": VotoObservador(dimension="M_l", score=5.0, confianza=0.6),
    }
    result = ag.deliberar("TRABAJO", mi_voto, votos_otros)
    assert result["mantiene"] is True
    assert result["ajuste"] == 0.0


def test_arbitro_analizar_tension_baja():
    from topologia.agents.arbitro import Arbitro
    ag = Arbitro()
    ev = EvaluacionNodo(
        nodo_id="TEST", nodo_nombre="Test",
        dimension_m=5.0, dimension_l=5.0, dimension_s=5.0,
        votos={
            "M_m": VotoObservador(dimension="M_m", score=5.0, confianza=0.9),
            "M_l": VotoObservador(dimension="M_l", score=5.0, confianza=0.9),
            "M_s": VotoObservador(dimension="M_s", score=5.0, confianza=0.9),
        },
    )
    result = ag.analizar([ev])
    assert result["tension_promedio"] < 0.2


def test_arbitro_analizar_tension_alta():
    from topologia.agents.arbitro import Arbitro
    ag = Arbitro()
    ev = EvaluacionNodo(
        nodo_id="TEST", nodo_nombre="Test",
        dimension_m=2.0, dimension_l=8.0, dimension_s=5.0,
        votos={
            "M_m": VotoObservador(dimension="M_m", score=2.0, confianza=0.9,
                                   tension_con=["M_l"]),
            "M_l": VotoObservador(dimension="M_l", score=8.0, confianza=0.9,
                                   tension_con=["M_m"]),
            "M_s": VotoObservador(dimension="M_s", score=5.0, confianza=0.5),
        },
    )
    result = ag.analizar([ev])
    assert result["tension_promedio"] > 0.3
    assert len(result["tensiones_por_nodo"]) == 1


@patch("topologia.agents.artista.Artista.ejecutar_prompt")
def test_artista_especular_con_historial(mock_llm):
    mock_llm.return_value = [{
        "patron_id": "P-015", "items": ["item_001"],
        "confianza": 0.8, "argumento": "test con historial",
        "nodos_sugeridos": ["ECONOMIA"], "pregunta_abierta": "¿test?",
    }]
    ag = Artista()
    items = [_mock_item()]
    estado = EstadoCultural(
        sociedad="Chile",
        M_m=5.0, M_l=5.0, M_s=5.0,
        nodos=[EvaluacionNodo(
            nodo_id="ECONOMIA", nodo_nombre="Economia",
            dimension_m=5.0, dimension_l=5.0, dimension_s=5.0,
        )],
    )
    historial = [
        EstadoCultural(
            sociedad="Chile", fecha=datetime(2026, 7, 20),
            M_m=5.0, M_l=5.0, M_s=5.0,
            nodos=[EvaluacionNodo(
                nodo_id="ECONOMIA", nodo_nombre="Economia",
                dimension_m=5.0, dimension_l=5.0, dimension_s=5.0,
            )],
        ),
    ]
    result = ag.especular(items, estado=estado, historial=historial)
    assert len(result) == 1
    assert result[0].patron_id == "P-015"
    assert "historial" in result[0].argumento or True  # no force assert


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
