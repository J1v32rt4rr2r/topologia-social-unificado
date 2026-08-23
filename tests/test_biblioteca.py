"""Pruebas para la biblioteca diaria (snapshot + consolidación)."""

import json
from datetime import date

from topologia.biblioteca import (
    backfill_dias_pasados,
    consolidar_dia,
    get_biblioteca_dir,
    guardar_items_crudos,
)

_SOCIEDAD = "Chile"


def _esqueleto(base, fecha: date):
    """Crea el árbol de día mínimo (estado, reporte_json, informe y riesgo)."""
    estados = base / "estados"
    estados.mkdir(parents=True, exist_ok=True)
    (estados / f"{_SOCIEDAD}_{fecha.isoformat()}.json").write_text(
        json.dumps({"sociedad": _SOCIEDAD, "fecha": "2026-08-21T06:00:00"}),
        encoding="utf-8",
    )
    (base / "reportes_json").mkdir(parents=True, exist_ok=True)
    (base / "reportes_json" / f"{_SOCIEDAD}_{fecha.isoformat()}.json").write_text(
        json.dumps({"resumen_ejecutivo": "x"}), encoding="utf-8"
    )
    reportes = base / "reportes"
    (reportes / "redes_riesgo").mkdir(parents=True, exist_ok=True)
    (reportes / "redes_riesgo" / f"red_riesgo_{fecha.isoformat()}.json").write_text(
        "{}", encoding="utf-8"
    )
    informe = reportes / f"informe_{_SOCIEDAD}_{fecha.isoformat()}_0600.html"
    informe.write_text("<html></html>", encoding="utf-8")
    return base


def _leer_manifest(base, fecha: date):
    ruta = get_biblioteca_dir(base) / fecha.isoformat() / _SOCIEDAD / "manifest.json"
    return json.loads(ruta.read_text(encoding="utf-8"))


def test_backfill_nivel_parcial(tmp_path):
    fecha = date(2026, 7, 18)
    _esqueleto(tmp_path, fecha)

    dias = backfill_dias_pasados(
        sociedad=_SOCIEDAD, data_dir=tmp_path, desde=fecha
    )

    assert dias == [get_biblioteca_dir(tmp_path) / fecha.isoformat() / _SOCIEDAD]
    manifest = _leer_manifest(tmp_path, fecha)
    assert manifest["nivel"] == "parcial"
    assert not manifest["estrategia_presente"]
    tipos = {a["tipo"]: a["archivo"] for a in manifest["archivos"]}
    assert tipos["estado"] == "estado.json"
    assert tipos["informe_json"] == "informe.json"
    assert "graficos" not in " ".join(tipos.values())


def test_ciclo_genera_nivel_completo(tmp_path):
    fecha = date(2026, 8, 21)
    _esqueleto(tmp_path, fecha)

    class Item:
        def __init__(self, ident, titulo, fuente, nodo):
            self.id = ident
            self.titulo = titulo
            self.fuente = fuente
            self.nodo_sugerido = nodo
            self.url, self.contenido, self.tags = "", "cuerpo", []
            self.dimension_sugerida, self.score_relevancia = "", 0.7

    items = [
        Item("1", "Noticia economía", "elciudadano", "ECONOMIA"),
        Item("2", "Trabajo precario", "cambio21", "TRABAJO"),
    ]

    class Estrategia:
        def model_dump(self, mode="json"):
            return {"nodos_prioritarios": ["ECONOMIA", "TRABAJO"]}

    guardar_items_crudos(items, Estrategia(), fecha, data_dir=tmp_path, sociedad=_SOCIEDAD)
    consolidar_dia(fecha, data_dir=tmp_path, sociedad=_SOCIEDAD)

    manifest = _leer_manifest(tmp_path, fecha)
    assert manifest["nivel"] == "completo"
    assert manifest["estrategia_presente"]
    assert "por_fuente" in manifest["conteos"]


def test_consolidar_dia_idempotente(tmp_path):
    fecha = date(2026, 8, 22)
    _esqueleto(tmp_path, fecha)

    consolidar_dia(fecha, data_dir=tmp_path, sociedad=_SOCIEDAD)
    consolidar_dia(fecha, data_dir=tmp_path, sociedad=_SOCIEDAD)

    manifest = _leer_manifest(tmp_path, fecha)
    assert [a["archivo"] for a in manifest["archivos"]] == [
        "estado.json",
        "informe.json",
        "informe.html",
        "riesgo.json",
    ]


def test_shot_guardar_items_recorta_titulo(tmp_path):
    fecha = date(2026, 8, 23)
    (tmp_path / "estados").mkdir(parents=True, exist_ok=True)

    item = {"id": "1", "titulo": "x" * 300}
    guardar_items_crudos([item], {"n": 1}, fecha, data_dir=tmp_path, sociedad=_SOCIEDAD)

    crudo = get_biblioteca_dir(tmp_path) / fecha.isoformat() / _SOCIEDAD / "items.json"
    guardados = json.loads(crudo.read_text(encoding="utf-8"))
    assert len(guardados[0]["titulo"]) == 300
    assert "contenido" in guardados[0]
    assert guardados[0]["id"] == "1"