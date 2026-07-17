"""Tests de DecisionDB (memoria del sistema)."""

import json
import tempfile
from pathlib import Path

import pytest

from topologia.memoria.decisiones import DecisionDB
from topologia.models.schemas import EstadoPatron, PatronAnalogico


@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as tmp:
        yield DecisionDB(ruta=tmp)


class TestRegistro:
    def test_registrar_y_listar(self, db):
        db.registrar("observation", "test content")
        entries = db.listar()
        assert len(entries) == 1
        assert entries[0]["contenido"] == "test content"

    def test_registrar_con_tags(self, db):
        db.registrar("decision", "una decisión", tags=["importante"])
        entries = db.listar(tag="importante")
        assert len(entries) == 1

    def test_tipo_invalido(self, db):
        with pytest.raises(ValueError):
            db.registrar("invalido", "contenido")

    def test_filtrar_por_tipo(self, db):
        db.registrar("observation", "obs1")
        db.registrar("decision", "dec1")
        entries = db.listar(tipo="decision")
        assert len(entries) == 1


class TestPatrones:
    def test_patrones_vacio(self, db):
        assert db.patrones() == []

    def test_guardar_y_recuperar(self, db):
        p = PatronAnalogico(id="P001", forma="espiral", significado="ciclo")
        db.guardar_patron(p)
        assert len(db.patrones()) == 1
        assert db.patron_por_id("P001") is not None

    def test_patron_no_existente(self, db):
        assert db.patron_por_id("NO_EXISTE") is None

    def test_validar_patron(self, db):
        p = PatronAnalogico(id="P001", forma="espiral", significado="ciclo")
        db.guardar_patron(p)
        db.validar_patron("P001", EstadoPatron.validado)
        actualizado = db.patron_por_id("P001")
        assert actualizado is not None
        assert actualizado.estado == EstadoPatron.validado
        assert actualizado.veces_validado == 1
        assert actualizado.veces_estudiado == 1

    def test_validar_patron_inexistente_no_rompe(self, db):
        db.validar_patron("NO_EXISTE", EstadoPatron.validado)
        assert db.patrones() == []


class TestSincronizacion:
    def test_sincronizar_desde(self, db):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump([{"id": "ext-1", "tipo": "observation", "contenido": "externo", "tags": [], "timestamp": "2024-01-01"}], f)
            f.flush()
            db.sincronizar_desde(f.name)
        entries = db.listar()
        assert len(entries) == 1
        Path(f.name).unlink(missing_ok=True)

    def test_sincronizar_archivo_inexistente(self, db):
        db.sincronizar_desde("/no/existe.json")
        assert db.listar() == []


class TestEstadisticas:
    def test_estadisticas_vacias(self, db):
        stats = db.estadisticas()
        assert stats["total"] == 0
        assert stats["por_tipo"] == {}
        assert stats["patrones"] == 0
        assert stats["validados"] == 0

    def test_estadisticas_con_datos(self, db):
        db.registrar("observation", "obs1")
        db.registrar("decision", "dec1")
        p = PatronAnalogico(id="P001", forma="linea", significado="direccion")
        db.guardar_patron(p)
        db.validar_patron("P001", EstadoPatron.validado)
        stats = db.estadisticas()
        assert stats["total"] == 2
        assert stats["patrones"] == 1
        assert stats["validados"] == 1
