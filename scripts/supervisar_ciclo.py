"""Supervisor del ciclo de observación diario (06:00).

Vigila la ejecución del ciclo diario mientras corre: hace polling continuo
del log (`data/logs/ciclo_YYYY-MM-DD.log`), del proceso (`python -m
topologia.main daily`) y del informe generado, y emite un veredicto final:

  COMPLETED     → el ciclo terminó y dejó su informe HTML
  RUNNING       → el ciclo sigue vivo (estado intermedio)
  FAILED        → la ventana máxima se agotó sin informe (o sin proceso vivo)
  NEVER_STARTED → no hubo log para la fecha

Si llega a la ventana límite sin completar y quedan reintentos, relanza
`ciclo_diario.ps1` y continúa vigilando.

Uso:
    python scripts/supervisar_ciclo.py
    python scripts/supervisar_ciclo.py --fecha 2026-08-19 --analizar
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, time as dt_time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_LOGS_DIR = _BASE / "data" / "logs"
_CICLO_SCRIPT = _BASE / "ciclo_diario.ps1"
_HORA_INICIO_CICLO = 6

sys.path.insert(0, str(_BASE / "src"))

from topologia.paths import get_reportes_dir  # noqa: E402

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - la consola sin UTF-8 no debe tumbar el supervisor
        pass

_RE_CICLO = re.compile(r"=== CICLO DIARIO ===")
_RE_TIEMPO = re.compile(r"(\d{2}):(\d{2}):(\d{2})")
_RE_RSS = re.compile(r"RSS total:\s*(\d+)\s*items .*? de (\d+)\s*brutos")
_RE_FILTRO_CHILE = re.compile(r"Filtro Chile:\s*(\d+)\s*items descartados")
_RE_RELEVANCIA = re.compile(r"Filtro de relevancia:\s*(\d+)[^\d]+(\d+)")
_RE_COBERTURA = re.compile(
    r"(?:Cobertura de datos:\s*|\[\s*COBERTURA\s*\]\s*)(\d+)/(\d+)"
)
_RE_INFORME = re.compile(r"Informe generado:\s*(.+?\.html)")
_RE_DELTA = re.compile(r"coherencia\s+\w+.*?\([^)]*?([\d.]+)")
_RE_RESUMEN = re.compile(r"Resumen:\s*(.+)")
_RE_ERROR = re.compile(r"\bCRITICAL\b|Traceback|LLM falló")

RSS_BRUTOS_MIN, RSS_BRUTOS_MAX = 150, 400
FILTRO_CHILE_MIN, FILTRO_CHILE_MAX = 30, 70
COBERTURA_MIN = 8
DURACION_ALERTA_MIN = 180


@dataclass
class AnalisisCiclo:
    bloque: str = ""
    iniciado: bool = False
    hay_log: bool = False
    tamano_bytes: int = 0
    log_mtime: float | None = None
    rss_unicos: int | None = None
    rss_brutos: int | None = None
    filtro_chile: int | None = None
    cobertura: int | None = None
    cobertura_total: int | None = None
    delta: float | None = None
    resumen: str | None = None
    informe_linea: str | None = None
    informe: Path | None = None
    errores: int = 0
    inicio_local: datetime | None = None
    duracion_min: float | None = None
    warnings: list[str] = field(default_factory=list)


def _reparar_mojibake(texto: str) -> str:
    """Recupera texto doblemente codificado por el `*>>` de PowerShell.

    Python escribe UTF-8 a stdout; PowerShell lo decodifica con la página de
    códigos OEM (cp437/cp850) y lo regraba en UTF-16. Se revierte la cadena.
    """
    for codepage in ("cp437", "cp850"):
        try:
            return texto.encode(codepage).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return texto


def _leer_log(ruta: Path) -> tuple[str, int]:
    """Lee el log del ciclo detectando BOM (PowerShell `*>>` escribe UTF-16-LE)."""
    try:
        datos = ruta.read_bytes()
    except OSError:
        return "", 0
    if datos.startswith((b"\xff\xfe", b"\xfe\xff")):
        texto = datos.decode("utf-16", errors="replace")
    elif datos.startswith(b"\xef\xbb\xbf"):
        texto = datos.decode("utf-8-sig", errors="replace")
    else:
        texto = datos.decode("utf-8", errors="replace")
    return _reparar_mojibake(texto), len(datos)


def _analizar_log(texto: str, reportes: Path, fecha: date, sociedad: str) -> AnalisisCiclo:
    a = AnalisisCiclo()
    a.hay_log = bool(texto)
    a.tamano_bytes = len(texto.encode("utf-8", "replace"))
    marcas = list(_RE_CICLO.finditer(texto))
    a.iniciado = bool(marcas)
    bloque = texto[marcas[-1].start():] if marcas else texto

    m_rss = re.search(_RE_RSS.pattern, bloque)
    if m_rss:
        a.rss_unicos, a.rss_brutos = int(m_rss.group(1)), int(m_rss.group(2))
    m_chile = re.search(_RE_FILTRO_CHILE.pattern, bloque)
    if m_chile:
        a.filtro_chile = int(m_chile.group(1))
    coberturas = list(_RE_COBERTURA.finditer(bloque))
    if coberturas:
        ultima = coberturas[-1]
        a.cobertura = int(ultima.group(1))
        a.cobertura_total = int(ultima.group(2))
    m_informe = list(_RE_INFORME.finditer(texto))
    if m_informe:
        a.informe_linea = m_informe[-1].group(1).strip()
    m_delta = re.search(_RE_DELTA.pattern, bloque)
    if m_delta:
        try:
            a.delta = float(m_delta.group(1))
        except ValueError:
            a.delta = None
    m_resumen = re.search(_RE_RESUMEN.pattern, bloque)
    if m_resumen:
        a.resumen = m_resumen.group(1).strip()
    a.errores = len(_RE_ERROR.findall(texto))

    m_tiempo = re.search(_RE_TIEMPO.pattern, bloque)
    if m_tiempo:
        h, m, s = (int(x) for x in m_tiempo.groups())
        a.inicio_local = datetime.combine(fecha, dt_time(h, m, s))

    patron_informe = f"informe_{sociedad}_{fecha.isoformat()}*.html"
    informes = sorted(reportes.glob(patron_informe), key=lambda p: p.stat().st_mtime)
    if informes:
        a.informe = informes[-1]
        if a.inicio_local:
            a.duracion_min = (
                a.informe.stat().st_mtime - a.inicio_local.timestamp()
            ) / 60.0
    return a


def _clasificar(a: AnalisisCiclo, proceso_activo: bool) -> list[str]:
    if a.informe is not None:
        return ["COMPLETED"]
    if not a.hay_log:
        return ["NEVER_STARTED"]
    if not a.iniciado:
        return ["FAILED"]
    if proceso_activo:
        return ["RUNNING"]
    return ["FAILED"]


def _chequear_rangos(a: AnalisisCiclo) -> list[str]:
    warnings: list[str] = []
    if a.rss_brutos is not None and not (RSS_BRUTOS_MIN <= a.rss_brutos <= RSS_BRUTOS_MAX):
        warnings.append(
            f"RSS brutos fuera de rango ({a.rss_brutos}, esperado {RSS_BRUTOS_MIN}-{RSS_BRUTOS_MAX})"
        )
    if a.filtro_chile is not None and not (
        FILTRO_CHILE_MIN <= a.filtro_chile <= FILTRO_CHILE_MAX
    ):
        warnings.append(
            f"Filtro Chile fuera de rango ({a.filtro_chile}, "
            f"esperado {FILTRO_CHILE_MIN}-{FILTRO_CHILE_MAX})"
        )
    if a.cobertura is not None and a.cobertura < COBERTURA_MIN:
        warnings.append(f"Cobertura baja ({a.cobertura}/{a.cobertura_total or 9})")
    if a.errores:
        warnings.append(f"Errores críticos en el log: {a.errores} (CRITICAL/Traceback/LLM falló)")
    if a.duracion_min is not None and a.duracion_min > DURACION_ALERTA_MIN:
        warnings.append(f"Duración elevada ({a.duracion_min:.0f} min > {DURACION_ALERTA_MIN} min)")
    return warnings


def _proceso_ciclo_activo() -> bool:
    script = (
        "$p = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
        "-ErrorAction SilentlyContinue; "
        "@($p | Where-Object { $_.CommandLine -match 'topologia\\.main daily' }).Count"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NoLogo", "-Command", script],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            return int(proc.stdout.strip() or 0) > 0
        except ValueError:
            return False
    except Exception as e:  # noqa: BLE001 - el supervisor no debe caer por el probe
        _log(f"AVISO | No se pudo consultar el proceso activo: {e}")
        return False


def _ahora() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _log(mensaje: str, archivo: Path | None = None) -> None:
    linea = f"{_ahora()} | {mensaje}"
    print(linea, flush=True)
    if archivo is not None:
        with archivo.open("a", encoding="utf-8") as fh:
            fh.write(linea + "\n")


def _crear_veredicto(a: AnalisisCiclo, estado: str, reintentos_usados: int) -> list[str]:
    lineas = [
        "=== VEREDICTO ===",
        f"Estado: {estado}",
        f"Log: {a.tamano_bytes} bytes, iniciado={a.iniciado}",
    ]
    if a.inicio_local:
        lineas.append(f"Inicio detectado: {a.inicio_local.strftime('%H:%M:%S')}")
    if a.duracion_min is not None:
        lineas.append(f"Duración: {a.duracion_min:.0f} min")
    if a.rss_brutos is not None:
        lineas.append(f"RSS: {a.rss_unicos} únicos de {a.rss_brutos} brutos")
    if a.filtro_chile is not None:
        lineas.append(f"Filtro Chile: {a.filtro_chile} descartados")
    if a.cobertura is not None:
        lineas.append(
            f"Cobertura: {a.cobertura}/{a.cobertura_total or 9} nodos"
        )
    if a.delta is not None:
        lineas.append(f"Coherencia: δ={a.delta}°")
    if a.informe is not None:
        lineas.append(f"Informe: {a.informe}")
    if a.resumen:
        lineas.append(f"Resumen: {a.resumen}")
    if reintentos_usados:
        lineas.append(f"Reintentos usados: {reintentos_usados}")
    return lineas


def _relanzar_ciclo(archivo: Path) -> bool:
    _log(f"ACCION | Relanzando ciclo: {_CICLO_SCRIPT}")
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(_CICLO_SCRIPT),
            ],
            cwd=str(_BASE),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except Exception as e:  # noqa: BLE001
        _log(f"ERROR | No se pudo relanzar el ciclo: {e}", archivo)
        return False


def _supervisar(args: argparse.Namespace) -> int:
    fecha = args.fecha
    reportes = get_reportes_dir()
    if not reportes.exists():
        reportes = _BASE / "data" / "reportes"
    log_path = args.log_dir / f"ciclo_{fecha.isoformat()}.log"
    sup_log = (
        None
        if args.analizar
        else args.log_dir / f"supervision_{fecha.isoformat()}.log"
    )
    if sup_log is not None:
        sup_log.parent.mkdir(parents=True, exist_ok=True)

    reintentos_restantes = args.reintentos
    reintentos_usados = 0
    ventana_seg = args.ventana_max_min * 60
    arranque = time.monotonic()
    retry_parcial: bool = False

    if not args.analizar:
        _log(
            "INICIO | Supervisión del ciclo diario "
            f"(intervalo={args.intervalo_seg}s, ventana={args.ventana_max_min}min, "
            f"reintentos={args.reintentos})",
            sup_log,
        )

    while True:
        texto, nbytes = _leer_log(log_path) if log_path.exists() else ("", 0)
        a = _analizar_log(texto, reportes, fecha, args.sociedad)
        a.tamano_bytes = nbytes
        if log_path.exists():
            a.log_mtime = log_path.stat().st_mtime
        proceso = _proceso_ciclo_activo()
        estado = _clasificar(a, proceso)[0]
        a.warnings = _chequear_rangos(a)

        if not args.analizar:
            _log(
                f"ESTADO | {estado} | log={a.tamano_bytes}B "
                f"iniciado={a.iniciado} proceso={proceso} "
                f"rss_brutos={a.rss_brutos} filtro_chile={a.filtro_chile}",
                sup_log,
            )
            if (
                estado == "RUNNING"
                and a.log_mtime is not None
                and time.time() - a.log_mtime > args.stall_min * 60
                and a.tamano_bytes > 0
            ):
                _log(
                    "AVISO | Proceso vivo pero log sin crecimiento desde "
                    f"{datetime.fromtimestamp(a.log_mtime).strftime('%H:%M:%S')} "
                    f"(>{args.stall_min} min) — posible atascamiento, no se aborta",
                    sup_log,
                )

        if estado == "COMPLETED":
            lineas = _crear_veredicto(a, estado, reintentos_usados)
            if a.warnings:
                lineas.append("Advertencias:")
                lineas.extend(f"  - {w}" for w in a.warnings)
            resumen = "\n".join(lineas)
            _log("VEREDICTO | COMPLETED", sup_log)
            print(resumen, flush=True)
            if not args.analizar:
                with sup_log.open("a", encoding="utf-8") as fh:
                    fh.write(resumen + "\n")
            return 0

        if args.analizar:
            if estado == "NEVER_STARTED":
                _log("VEREDICTO | NEVER_STARTED (sin log ni informe para la fecha)")
                return 2
            _log(
                f"VEREDICTO | {estado} (sin informe para {fecha.isoformat()}, "
                f"proceso={proceso}, log_iniciado={a.iniciado})"
            )
            return 1

        elapsed = time.monotonic() - arranque
        if elapsed >= ventana_seg:
            if estado in ("FAILED", "NEVER_STARTED") and reintentos_restantes > 0:
                reintentos_restantes -= 1
                reintentos_usados += 1
                retry_parcial = _relanzar_ciclo(sup_log)
                arranque = time.monotonic()
                _log(
                    f"RETRY | Reintento {reintentos_usados} lanzado (estado previo {estado}, "
                    f"relanzado={retry_parcial}); nueva ventana de {args.ventana_max_min} min",
                    sup_log,
                )
                if retry_parcial:
                    continue
            lineas = _crear_veredicto(a, "FAILED", reintentos_usados)
            lineas.append("Motivo: ventana máxima agotada sin informe")
            resumen = "\n".join(lineas)
            _log("VEREDICTO | FAILED", sup_log)
            print(resumen, flush=True)
            with sup_log.open("a", encoding="utf-8") as fh:
                fh.write(resumen + "\n")
            return 1

        time.sleep(args.intervalo_seg)


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Supervisa el ciclo diario (06:00) de observación cultural."
    )
    parser.add_argument("--fecha", type=date.fromisoformat, default=date.today())
    parser.add_argument("--sociedad", default="Chile")
    parser.add_argument("--log-dir", type=Path, default=_LOGS_DIR)
    parser.add_argument("--intervalo-seg", type=int, default=300)
    parser.add_argument("--ventana-max-min", type=int, default=180)
    parser.add_argument("--stall-min", type=int, default=30)
    parser.add_argument("--reintentos", type=int, default=1)
    parser.add_argument(
        "--analizar",
        action="store_true",
        help="Análisis único sin polling ni reintentos (para validación histórica).",
    )
    args = parser.parse_args()
    return _supervisar(args)


if __name__ == "__main__":
    sys.exit(_main())