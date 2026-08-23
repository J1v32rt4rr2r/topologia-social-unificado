"""Backfill de la biblioteca diaria: consolida los días ya persistidos.

Crea `biblioteca/YYYY-MM-DD/` (nivel "parcial", sin ítems crudos) para todos
los días con estado guardado. A partir de la puesta en marcha, el ciclo diario
deja la carpeta "completo" (con items.json y estrategia.json).

Uso:
    python scripts/backfill_biblioteca.py
    python scripts/backfill_biblioteca.py --desde 2026-07-01
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE / "src"))

from topologia.biblioteca import backfill_dias_pasados  # noqa: E402


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Consolida la biblioteca diaria para los días ya persistidos."
    )
    parser.add_argument("--sociedad", default="Chile")
    parser.add_argument(
        "--desde", type=date.fromisoformat, default=None,
        help="Solo días desde esta fecha (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--data-dir", type=Path, default=None,
        help="Ruta alternativa de datos (pruebas).",
    )
    args = parser.parse_args()

    dias = backfill_dias_pasados(
        sociedad=args.sociedad, data_dir=args.data_dir, desde=args.desde
    )
    print(f"Biblioteca actualizada: {len(dias)} días consolidados")
    for d in dias:
        print(f"  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())