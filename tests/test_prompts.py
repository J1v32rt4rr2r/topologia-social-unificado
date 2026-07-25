"""Tests para el cargador de prompts desde archivos."""

from pathlib import Path

from topologia.prompts import PromptLoader


def test_prompt_loader_carga_archivo():
    loader = PromptLoader()
    content = loader.load("artista_noticias", patrones_en_memoria="test", items_del_dia="test2")
    assert "test" in content
    assert "test2" in content
    assert "Artista" in content


def test_prompt_loader_todas_las_variables():
    loader = PromptLoader()
    content = loader.load("estadista_evaluar",
        nodo="ECONOMIA",
        pregunta_nodo="¿Test?",
        items_del_nodo="noticia1",
        score_anterior="5.0",
        justificacion_anterior="estable",
    )
    assert "ECONOMIA" in content
    assert "noticia1" in content
    assert "ESTANCIA (M_m)" in content


def test_prompt_loader_todas_los_archivos():
    loader = PromptLoader()
    esperados = [
        "artista_noticias", "artista_taller",
        "estadista_evaluar", "estadista_validar", "estadista_deliberar",
        "filosofo_evaluar", "filosofo_validar", "filosofo_deliberar",
        "sociologo_evaluar", "sociologo_validar", "sociologo_deliberar",
        "redactor_sintesis",
        "arbitro_deliberacion",
    ]
    for name in esperados:
        content = loader.load(name)
        assert content, f"Prompt vacío: {name}"


def test_prompt_loader_file_not_found():
    loader = PromptLoader()
    try:
        loader.load("no_existe")
        assert False, "Debió lanzar FileNotFoundError"
    except FileNotFoundError:
        pass


def test_prompt_loader_ruta_personalizada(tmp_path):
    archivo = tmp_path / "test.md"
    archivo.write_text("Hola {nombre}!", encoding="utf-8")
    loader = PromptLoader(prompts_dir=str(tmp_path))
    content = loader.load("test", nombre="Mundo")
    assert content == "Hola Mundo!"
