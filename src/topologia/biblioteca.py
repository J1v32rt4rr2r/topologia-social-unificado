"""Biblioteca diaria de datos obtenidos por el ciclo de observación.

Cada día se consolida una carpeta inmutable `biblioteca/YYYY-MM-DD/` que
permite re-medir/recalibrar a posteriori sin re-ejecutar el ciclo:

  manifest.json   - índice con metadatos, checksums y origen de cada archivo
  estado.json     - copia del estado cultural calculado (dimensiones, deltas)
  informe.json    - copia del informe del redactor (resumen, alertas, pan)
  informe.html    - copia del informe HTML renderizado
  riesgo.json     - copia de la red de riesgo del día
  items.json      - snapshot de los ítems crudos recolectados (fuente, nodo, score)
  estrategia.json - estrategia de recolección usada (prioritarios, pesos, umbral)
  log.txt         - copia del log del ciclo de ese día
  graficos/       - gráficos, timeline y modelos generados ese día

Los días previos a la puesta en marcha se consolidan en modo "parcial"
(sin items.json ni estrategia.json), marcado en el manifest.

Dependencias: solo stdlib + pydantic (via model_dump de los schemas).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Any

from topologia.logger import logger
from topologia.paths import get_data_dir

ESQUEMA_BIBLIOTECA = 1
_ORIGEN_ESTADOS = "estados"
_ORIGEN_REPORTES_JSON = "reportes_json"
_ORIGEN_REDES_RIESGO = "reportes/redes_riesgo"


def get_biblioteca_dir(data_dir: Path | None = None) -> Path:
    base = data_dir or get_data_dir()
    return base / "biblioteca"


def _dia_dir(data_dir: Path | None, fecha: date, sociedad: str) -> Path:
    return get_biblioteca_dir(data_dir) / fecha.isoformat() / sociedad


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _datos_item(it: Any) -> dict:
    if isinstance(it, dict):
        datos = dict(it)
    else:
        datos = {
            "id": getattr(it, "id", ""),
            "titulo": getattr(it, "titulo", "") or "",
            "fuente": getattr(it, "fuente", ""),
            "url": getattr(it, "url", "") or "",
            "fecha": getattr(it, "fecha", datetime.now()).isoformat(),
            "contenido": getattr(it, "contenido", "") or "",
            "tags": list(getattr(it, "tags", []) or []),
            "nodo_sugerido": getattr(it, "nodo_sugerido", "") or "",
            "dimension_sugerida": getattr(it, "dimension_sugerida", "") or "",
            "score_relevancia": float(getattr(it, "score_relevancia", 0.0) or 0.0),
        }
    for clave, vacio in _CAMPOS_VACIOS.items():
        datos.setdefault(clave, vacio)
    datos["titulo"] = (datos["titulo"] or "")[:300]
    return datos


_CAMPOS_VACIOS: dict = {
    "id": "",
    "fuente": "",
    "url": "",
    "contenido": "",
    "tags": [],
    "nodo_sugerido": "",
    "dimension_sugerida": "",
    "score_relevancia": 0.0,
}


def _estrategia_datos(estrategia: Any) -> dict:
    if estrategia is None:
        return {}
    if hasattr(estrategia, "model_dump"):
        return estrategia.model_dump(mode="json")
    if isinstance(estrategia, dict):
        return estrategia
    return {}


def guardar_items_crudos(
    items: list,
    estrategia: Any,
    fecha: date,
    sociedad: str = "Chile",
    data_dir: Path | None = None,
) -> Path | None:
    """Persiste el snapshot de ítems y la estrategia en la carpeta del día."""
    dia = _dia_dir(data_dir, fecha, sociedad)
    dia.mkdir(parents=True, exist_ok=True)
    try:
        (dia / "items.json").write_text(
            json.dumps([_datos_item(it) for it in items], indent=1, ensure_ascii=False),
            encoding="utf-8",
        )
        (dia / "estrategia.json").write_text(
            json.dumps(_estrategia_datos(estrategia), indent=1, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"Biblioteca: snapshot de {len(items)} ítems crudos en {dia}")
        return dia
    except Exception as exc:  # noqa: BLE001 - captura incompleta no debe tumbar el ciclo
        logger.warning(f"Biblioteca: no se pudo guardar ítems crudos: {exc}")
        return None


def _copiar(archivo: Path, destino: Path) -> bool:
    if not archivo.exists():
        return False
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archivo, destino)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Biblioteca: no se pudo copiar {archivo.name}: {exc}")
        return False


def _conteos(items: list) -> dict:
    por_fuente: dict[str, int] = {}
    por_nodo: dict[str, int] = {}
    for it in items:
        fuente = (it.fuente or "desconocido") if not isinstance(it, dict) else (it.get("fuente") or "desconocido")
        nodo = it.nodo_sugerido if not isinstance(it, dict) else (it.get("nodo_sugerido") or "")
        por_fuente[fuente] = por_fuente.get(fuente, 0) + 1
        if nodo:
            por_nodo[nodo] = por_nodo.get(nodo, 0) + 1
    return {"por_fuente": dict(sorted(por_fuente.items())), "por_nodo": dict(sorted(por_nodo.items()))}


def consolidar_dia(
    fecha: date,
    sociedad: str = "Chile",
    data_dir: Path | None = None,
    forzar: bool = False,
) -> Path | None:
    """Consolida la carpeta del día copiando lo ya persistido y escribe el manifest.

    Copia: estado, informe (json + html), red de riesgo, log del ciclo y los
    artefactos de reportes cuyo mtime cae en ese día. Si no hay snapshot de
    ítems se marca nivel "parcial". Idempotente para una misma fecha.
    """
    import topologia.paths as paths_util

    base = data_dir or get_data_dir()
    dia = _dia_dir(data_dir, fecha, sociedad)
    dia.mkdir(parents=True, exist_ok=True)

    reportes_dir = (base / "reportes") if data_dir else getattr(paths_util, "get_reportes_dir")()
    estado_src = base / _ORIGEN_ESTADOS / f"{sociedad}_{fecha.isoformat()}.json"
    informe_src = base / _ORIGEN_REPORTES_JSON / f"{sociedad}_{fecha.isoformat()}.json"
    riesgo_src = reportes_dir / "redes_riesgo" / f"red_riesgo_{fecha.isoformat()}.json"
    log_src = Path(__file__).resolve().parents[2] / "data" / "logs" / f"ciclo_{fecha.isoformat()}.log"

    archivos: list[dict[str, Any]] = []

    def _registrar(tipo_orig: str, nombre: str, origen: Path, destino: Path) -> None:
        if not origen.exists():
            return
        if _copiar(origen, destino):
            archivos.append(
                {
                    "archivo": f"{destino.parent.name}/{destino.name}" if destino.parent != dia else destino.name,
                    "origen": str(origen),
                    "bytes": destino.stat().st_size,
                    "sha256": _sha256(destino),
                    "tipo": tipo_orig,
                }
            )

    _registrar("estado", "estado.json", estado_src, dia / "estado.json")
    _registrar("informe_json", "informe.json", informe_src, dia / "informe.json")

    informe_html = sorted(
        (reportes_dir).glob(f"informe_{sociedad}_{fecha.isoformat()}_*.html"),
        key=lambda p: p.stat().st_mtime,
    )
    if informe_html:
        _registrar("informe_html", "informe.html", informe_html[-1], dia / "informe.html")

    _registrar("riesgo", "riesgo.json", riesgo_src, dia / "riesgo.json")
    _registrar("log", "log.txt", log_src, dia / "log.txt")

    # Artefactos de reportes generados ese día (gráficos, timeline, modelos).
    if reportes_dir.exists():
        dia_inicio = datetime.combine(fecha, datetime.min.time()).timestamp()
        dia_fin = datetime.combine(fecha, datetime.max.time()).timestamp()
        graficos_dir = dia / "graficos"
        for archivo in sorted(reportes_dir.iterdir()):
            if not archivo.is_file():
                continue
            if archivo.suffix == ".html" and archivo.name.startswith("informe_"):
                continue
            if dia_inicio <= archivo.stat().st_mtime <= dia_fin:
                _registrar("grafico", f"graficos/{archivo.name}", archivo, graficos_dir / archivo.name)

    items_path = dia / "items.json"
    nivel = "parcial"
    conteos: dict = {}
    if items_path.exists():
        nivel = "completo"
        try:
            items = json.loads(items_path.read_text(encoding="utf-8"))
            conteos = _conteos(items)
        except Exception:  # noqa: BLE001
            conteos = {}

    manifest = {
        "esquema": ESQUEMA_BIBLIOTECA,
        "fecha": fecha.isoformat(),
        "sociedad": sociedad,
        "nivel": nivel,
        "generado_en": datetime.now().isoformat(),
        "archivos": archivos,
        "conteos": conteos,
        "estrategia_presente": (dia / "estrategia.json").exists(),
        "log": f"data/logs/ciclo_{fecha.isoformat()}.log",
    }
    (dia / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Biblioteca: día {fecha.isoformat()} consolidado (nivel={nivel}, {len(archivos)} archivos)")
    return dia


def backfill_dias_pasados(
    sociedad: str = "Chile",
    data_dir: Path | None = None,
    desde: date | None = None,
) -> list[Path]:
    """Consolida los días ya persistidos (modo parcial) hacia atrás."""
    from topologia.storage.store import FileStore

    base = data_dir or get_data_dir()
    store = FileStore(str(base)) if data_dir else FileStore()
    dias: list[Path] = []
    fechas = store.listar_estados(sociedad)
    for f in fechas:
        f_dt = date.fromisoformat(f)
        if desde and f_dt < desde:
            continue
        dia = consolidar_dia(f_dt, sociedad=sociedad, data_dir=data_dir)
        if dia:
            dias.append(dia)
    return dias