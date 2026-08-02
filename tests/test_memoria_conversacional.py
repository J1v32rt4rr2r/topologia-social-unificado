"""Tests de MemoriaRedactor (memoria conversacional del Redactor)."""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from topologia.memoria.conversacional import MemoriaRedactor, _estimar_tokens
from topologia.models.schemas import (
    EstadoCultural,
    Especulacion,
    InformeDiario,
    OperacionCinetica,
)


def _informe(texto: str) -> InformeDiario:
    return InformeDiario(
        panorama=texto,
        dinamicas="dinámicas breves del día",
        resumen_ejecutivo="resumen breve",
        mirada_adelante="mirada breve",
    )


def _estado(fecha: date) -> EstadoCultural:
    return EstadoCultural(
        fecha=fecha,
        sociedad="Chile",
        M_m=5.0,
        M_l=5.0,
        M_s=5.0,
        delta_promedio=30.0,
        coherente=True,
    )


@pytest.fixture
def memoria():
    with tempfile.TemporaryDirectory() as tmp:
        yield MemoriaRedactor(sociedad="Test", ruta=Path(tmp) / "mem.json", max_token_limit=2000)


def _resumen_fake(prompt, temperatura=0.2, max_tokens=600):
    return "Resumen generado: hitos y cambios del período."


class TestRegistroYContexto:
    def test_primer_dia_sin_historial(self, memoria):
        ctx = memoria.contexto()
        assert ctx["informe_anterior"] == ""
        assert ctx["metricas"]["buffer_tokens"] == 0

    def test_registrar_dia_agrega_buffer(self, memoria):
        memoria.registrar_dia(
            date(2026, 8, 1), _estado(date(2026, 8, 1)), [], [], _informe("Informe día 1")
        )
        m = memoria.metricas()
        assert m["buffer_mensajes"] == 2
        assert m["buffer_tokens"] > 0
        assert memoria.buffer[0]["role"] == "human"
        assert memoria.buffer[1]["role"] == "ai"
        assert "2026-08-01" in memoria.buffer[0]["content"]

    def test_contexto_incluye_dia(self, memoria):
        memoria.registrar_dia(date(2026, 8, 1), _estado(date(2026, 8, 1)), [], [], _informe("Informe día 1"))
        ctx = memoria.contexto()
        assert "ÚLTIMOS DÍAS" in ctx["informe_anterior"]
        assert "Informe día 1" in ctx["informe_anterior"]

    def test_registrar_sin_informe_no_crash(self, memoria):
        memoria.registrar_dia(date(2026, 8, 1), _estado(date(2026, 8, 1)))
        assert memoria.metricas()["buffer_mensajes"] == 1

    def test_round_trip_persistencia(self, memoria):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "mem.json"
            primera = MemoriaRedactor(sociedad="Test", ruta=ruta, max_token_limit=2000)
            primera.registrar_dia(date(2026, 8, 1), _estado(date(2026, 8, 1)), [], [], _informe("Informe día 1"))
            primera.registrar_dia(date(2026, 8, 2), _estado(date(2026, 8, 2)), [], [], _informe("Informe día 2"))
            recargada = MemoriaRedactor(sociedad="Test", ruta=ruta, max_token_limit=2000)
            assert recargada.metricas()["buffer_mensajes"] == 4
            assert recargada.ultima_fecha == "2026-08-02"


class TestPruning:
    def test_pruning_plega_mensajes_al_resumen(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = MemoriaRedactor(
                sociedad="Test", ruta=Path(tmp) / "mem.json",
                max_token_limit=100, llm=_resumen_fake,
            )
            for i in range(1, 8):
                m.registrar_dia(
                    date(2026, 8, i), _estado(date(2026, 8, i)),
                    [], [], _informe(f"Informe extenso del día {i} " * 10),
                )
            m2 = m.metricas()
            assert m2["resumen_rodante_tokens"] > 0
            assert m2["buffer_tokens"] <= 100
            assert m2["buffer_mensajes"] < 14

    def test_pruning_falla_y_no_pierde_mensajes(self):
        def llm_roto(prompt, temperatura=0.2, max_tokens=600):
            raise RuntimeError("API caída")

        with tempfile.TemporaryDirectory() as tmp:
            m = MemoriaRedactor(
                sociedad="Test", ruta=Path(tmp) / "mem.json",
                max_token_limit=100, llm=llm_roto,
            )
            # 2 días: supera el límite pero queda bajo la tolerancia (3x)
            for i in range(1, 3):
                m.registrar_dia(
                    date(2026, 8, i), _estado(date(2026, 8, i)),
                    [], [], _informe(f"Informe del día {i} " * 10),
                )
            m2 = m.metricas()
            assert m2["resumen_rodante_tokens"] == 0
            assert m2["buffer_mensajes"] == 4

    def test_pruning_registra_fecha_inicial_del_resumen(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = MemoriaRedactor(
                sociedad="Test", ruta=Path(tmp) / "mem.json",
                max_token_limit=100, llm=_resumen_fake,
            )
            for i in range(1, 4):
                m.registrar_dia(
                    date(2026, 8, i), _estado(date(2026, 8, i)),
                    [], [], _informe(f"Informe extenso del día {i} " * 10),
                )
            assert m.primer_dia_resumen == "2026-08-01"

    def test_archivado_mensual_tras_pruning(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = MemoriaRedactor(
                sociedad="Test", ruta=Path(tmp) / "mem.json",
                max_token_limit=100, llm=_resumen_fake,
            )
            # Días 1-2: disparan pruning y dejan resumen desde 08-01
            for i in range(1, 3):
                m.registrar_dia(
                    date(2026, 8, i), _estado(date(2026, 8, i)),
                    [], [], _informe(f"Informe extenso del día {i} " * 10),
                )
            assert m.primer_dia_resumen == "2026-08-01"
            # Día 31 (08-31): cruza 30 días desde 08-01 → archiva
            m.registrar_dia(
                date(2026, 8, 31), _estado(date(2026, 8, 31)),
                [], [], _informe("Informe extenso del día 31 " * 10),
            )
            assert len(m.memoria_permanente) == 1
            assert m.memoria_permanente[0]["desde"] == "2026-08-01"
            assert m.resumen_rodante == ""

    def test_tope_absoluto_sin_llm(self):
        def llm_roto(prompt, temperatura=0.2, max_tokens=600):
            raise RuntimeError("API caída")

        with tempfile.TemporaryDirectory() as tmp:
            m = MemoriaRedactor(
                sociedad="Test", ruta=Path(tmp) / "mem.json",
                max_token_limit=50, llm=llm_roto,
            )
            for i in range(1, 15):
                m.registrar_dia(
                    date(2026, 8, i), _estado(date(2026, 8, i)),
                    [], [], _informe(f"Informe del día {i} " * 10),
                )
            m2 = m.metricas()
            assert m2["buffer_tokens"] <= 50 * 3
            assert m2["buffer_mensajes"] > 0


class TestArchivadoMensual:
    def test_archivo_a_los_30_dias(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = MemoriaRedactor(
                sociedad="Test", ruta=Path(tmp) / "mem.json",
                max_token_limit=2000, llm=_resumen_fake,
            )
            m.registrar_dia(date(2026, 8, 1), _estado(date(2026, 8, 1)), [], [], _informe("Informe día 1"))
            # Forzamos resumen rodante manualmente (simula 30 días de resumen)
            m.resumen_rodante = "Resumen de agosto: hitos del mes."
            m.primer_dia_resumen = "2026-08-01"
            m.registrar_dia(date(2026, 9, 1), _estado(date(2026, 9, 1)), [], [], _informe("Informe día 2"))
            assert len(m.memoria_permanente) == 1
            assert m.memoria_permanente[0]["desde"] == "2026-08-01"
            assert m.memoria_permanente[0]["hasta"] == "2026-09-01"
            assert m.resumen_rodante == ""
            assert m.primer_dia_resumen is None
            ctx = m.contexto()
            assert "MEMORIA DE LARGO PLAZO" in ctx["informe_anterior"]
            assert "Resumen de agosto" in ctx["informe_anterior"]

    def test_no_archiva_antes_de_30_dias(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = MemoriaRedactor(
                sociedad="Test", ruta=Path(tmp) / "mem.json",
                max_token_limit=2000, llm=_resumen_fake,
            )
            m.resumen_rodante = "Resumen parcial"
            m.primer_dia_resumen = "2026-08-01"
            m.registrar_dia(date(2026, 8, 20), _estado(date(2026, 8, 20)), [], [], _informe("Informe"))
            assert len(m.memoria_permanente) == 0
            assert m.resumen_rodante == "Resumen parcial"

    def test_bloques_permanentes_acotados(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = MemoriaRedactor(
                sociedad="Test", ruta=Path(tmp) / "mem.json",
                max_token_limit=2000, llm=_resumen_fake,
            )
            for i in range(8):
                m.memoria_permanente.append({
                    "desde": f"2026-{i + 1:02d}-01", "hasta": f"2026-{i + 1:02d}-30",
                    "resumen": f"Bloque {i}",
                })
            ctx = m.contexto()
            assert len(m.memoria_permanente) == 8
            assert "Bloque 0" not in ctx["informe_anterior"]
            assert "Bloque 7" in ctx["informe_anterior"]
            assert ctx["metricas"]["bloques_permanentes"] == 8


class TestUtilidades:
    def test_estimar_tokens_no_cero(self):
        assert _estimar_tokens("") >= 0
        assert _estimar_tokens("texto de prueba" * 100) > 0

    def test_fecha_string(self, memoria):
        memoria.registrar_dia("2026-08-01", _estado(date(2026, 8, 1)), [], [], _informe("Informe"))
        assert memoria.ultima_fecha == "2026-08-01"

    def test_estado_y_opciones_en_contexto(self, memoria):
        op = OperacionCinetica(
            codigo="O3a", nombre="Tensión centro-periferia",
            intensidad=0.6, nodos_implicados=["economia"],
            descripcion="desborde",
        )
        esp = Especulacion(
            id="E1", patron_id="P1", confianza=0.7,
            argumento="hipótesis",
        )
        memoria.registrar_dia(
            date(2026, 8, 1), _estado(date(2026, 8, 1)),
            [op], [esp], _informe("Informe"),
            cobertura="economia: 3 items",
        )
        crudo = memoria.buffer[0]["content"]
        assert "O3a" in crudo
        assert "1 especulaciones" in crudo
        assert "cobertura: economia: 3 items" in crudo
