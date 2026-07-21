from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from topologia.storage.store import FileStore


NODOS = [
    "ECONOMIA", "TRABAJO", "CONTINUIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]


def main():
    store = FileStore()
    fechas = store.listar_estados("Chile")
    if not fechas:
        print("No hay estados guardados")
        return

    rows = []

    for i, fecha_str in enumerate(fechas):
        estado = store.cargar_estado("Chile", fecha_str)
        if not estado:
            continue

        gap = None
        if i > 0:
            dt_actual = datetime.strptime(fecha_str, "%Y-%m-%d")
            dt_prev = datetime.strptime(fechas[i - 1], "%Y-%m-%d")
            diff_h = (dt_actual - dt_prev).total_seconds() / 3600
            if diff_h > 30:
                gap = int(diff_h)

        nodos_data = {}
        for n in estado.nodos:
            nodos_data[n.nodo_id] = {
                "m": n.dimension_m,
                "l": n.dimension_l,
                "s": n.dimension_s,
                "delta": round(n.delta, 1),
                "fragil": "!" if n.fragil else "",
            }

        row = {
            "fecha": fecha_str,
            "era_k": estado.era_k,
            "M_m": estado.M_m,
            "M_l": estado.M_l,
            "M_s": estado.M_s,
            "delta": round(estado.delta_promedio, 1),
            "coherente": "OK" if estado.coherente else "NO",
            "theta_cultura": round(estado.theta_cultura, 1),
            "tension": round(estado.tension_total, 1),
            "fragiles": ", ".join(estado.nodos_fragiles) if estado.nodos_fragiles else "",
            "gap": gap,
        }
        row.update(nodos_data)
        rows.append(row)

    # Console output
    SEP = "=" * 110
    print()
    print(SEP)
    print("BARRIDO HISTORICO - Topologia Social")
    print(f"Periodo: {fechas[0]} -> {fechas[-1]}  |  {len(rows)} estados registrados")
    print(SEP)

    hdr = f"{'Fecha':<12} {'Era':>3} {'delta':>6} {'M_m':>5} {'M_l':>5} {'M_s':>5} {'theta':>6} {'tension':>7} {'Coh':>3} {'Gap':>5}  Fragiles"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        gap_str = f"+{r['gap']}h" if r["gap"] else ""
        frag = r["fragiles"]
        print(
            f"{r['fecha']:<12} "
            f"{r['era_k']:>3} "
            f"{r['delta']:>5.1f} "
            f"{r['M_m']:>5.1f} "
            f"{r['M_l']:>5.1f} "
            f"{r['M_s']:>5.1f} "
            f"{r['theta_cultura']:>5.1f} "
            f"{r['tension']:>7.0f} "
            f"{r['coherente']:>3} "
            f"{gap_str:>5}  "
            f"{frag}"
        )

    # Per-node matrix
    print()
    print(SEP)
    print("MATRIZ POR NODO (M_m / M_l / M_s)")
    print(SEP)

    for nid in NODOS:
        parts = []
        for r in rows:
            if nid not in r:
                continue
            nd = r[nid]
            parts.append(
                f"{r['fecha'][-5:]}: "
                f"{nd['m']:.1f}/{nd['l']:.1f}/{nd['s']:.1f}"
                f" d={nd['delta']} "
                f"{nd['fragil']}"
            )
        if parts:
            print(f"\n  {nid}:")
            print(f"    {'  |  '.join(parts)}")

    # Gaps
    gaps = [(r["fecha"], r["gap"]) for r in rows if r["gap"]]
    if gaps:
        print()
        print(SEP)
        print("GAPS (dias sin observacion)")
        for f, h in gaps:
            dias = h / 24
            print(f"  Antes de {f}: {h}h ({dias:.1f} dias) sin datos")

    # Save
    script_dir = Path(__file__).resolve().parent.parent
    out_dir = script_dir / "data" / "barrido"
    out_dir.mkdir(parents=True, exist_ok=True)

    csv = ["fecha,era_k,delta,M_m,M_l,M_s,theta,tension,coherente,gap_horas,fragiles"]
    for r in rows:
        csv.append(
            f"{r['fecha']},{r['era_k']},{r['delta']},{r['M_m']},{r['M_l']},{r['M_s']},"
            f"{r['theta_cultura']},{r['tension']},{r['coherente']},{r['gap'] or ''},\"{r['fragiles']}\""
        )
    (out_dir / "timeline.csv").write_text("\n".join(csv), encoding="utf-8")
    (out_dir / "timeline.json").write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")

    print()
    print(SEP)
    print(f"Datos guardados en: {out_dir / 'timeline.csv'}")
    print(SEP)


if __name__ == "__main__":
    main()
