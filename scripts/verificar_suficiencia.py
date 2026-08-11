"""Verificación de criterio habilitante para el vector de desarrollo temporal.

Revisa si los estados acumulados alcanzan la suficiencia exigida para que el
vector de desarrollo temporal y su plano complejo (fase) sean detectables:

  (a) n >= n_min
  (b) span >= ciclos_min * T_k  (ciclos completos por lógica)
  (c) todas las lógicas con status "estable"

Mientras `habilitado` sea False, los puntos 5 (distancias no recíprocas) y 6
(noticia = proyección de la lógica del emisor) quedan bloqueados.

Uso:
    python scripts/verificar_suficiencia.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE / "src"))

from topologia.math.armonicas import verificar_suficiencia  # noqa: E402
from topologia.paths import get_data_dir  # noqa: E402


def _cargar_series(
    sociedad: str,
) -> tuple[list[float], list[float], list[float], list[float]]:
    base = get_data_dir() / "estados"
    archivos = sorted(base.glob(f"{sociedad}_*.json"))
    t: list[float] = []
    m_m: list[float] = []
    m_l: list[float] = []
    m_s: list[float] = []
    ref: date | None = None
    for p in archivos:
        try:
            fecha = date.fromisoformat(p.stem.split("_")[-1])
        except ValueError:
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if ref is None:
            ref = fecha
        t.append((fecha - ref).days)
        m_m.append(d.get("m_m", 0.0))
        m_l.append(d.get("m_l", 0.0))
        m_s.append(d.get("m_s", 0.0))
    return t, m_m, m_l, m_s


def main() -> None:
    sociedad = "Chile"
    t, m_m, m_l, m_s = _cargar_series(sociedad)
    resultado = verificar_suficiencia(t, m_m, m_l, m_s)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    estado = "HABILITADO" if resultado["habilitado"] else "BLOQUEADO"
    print(f"\n==> Vector de desarrollo: {estado} (sociedad {sociedad})")


if __name__ == "__main__":
    main()