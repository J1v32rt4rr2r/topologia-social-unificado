from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import yaml

NODOS = [
    "ECONOMIA", "TRABAJO", "SEXUALIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]

with open(Path(__file__).resolve().parent.parent / "config" / "hitos.yaml", encoding="utf-8") as f:
    hitos = yaml.safe_load(f) or []

print("=== ACELERACIONES SIGNIFICATIVAS POR NODO ===\n")

for n in NODOS:
    rows = []
    for h in hitos:
        vel = h.get("velocidades", {}).get(n, {})
        acel = vel.get("aceleracion", 0) or 0
        vmedia = vel.get("media", 0)
        direccion = vel.get("direccion", "?")
        if abs(acel) > 0.1:
            rows.append((acel, h["id"], vmedia, direccion))
    if rows:
        rows.sort(key=lambda r: abs(r[0]), reverse=True)
        print(f"{n}:")
        for acel, pid, vmed, d in rows:
            print(f"  a={acel:+.3f}  v={vmed:+.3f}  {d}  [{pid}]")
        print()

print("=== NODOS CON ACELERACION SOSTENIDA (mismo signo en >1 hito) ===\n")
counts = defaultdict(lambda: {"pos": 0, "neg": 0})
for h in hitos:
    for n in NODOS:
        vel = h.get("velocidades", {}).get(n, {})
        acel = vel.get("aceleracion", 0) or 0
        if acel > 0.05:
            counts[n]["pos"] += 1
        elif acel < -0.05:
            counts[n]["neg"] += 1
for n in NODOS:
    c = counts[n]
    if c["pos"] + c["neg"] >= 2:
        print(f"  {n}: {c['pos']} pos / {c['neg']} neg  ({c['pos']+c['neg']} hitos con |a|>0.05)")

print("\n=== TOP VELOCIDAD MEDIA ABSOLUTA (todos los hitos) ===\n")
all_v = []
for h in hitos:
    for n in NODOS:
        vel = h.get("velocidades", {}).get(n, {})
        vmedia = vel.get("media", 0)
        if abs(vmedia) > 0.3:
            all_v.append((abs(vmedia), n, h["id"], vmedia))
all_v.sort(reverse=True)
for v, n, pid, vraw in all_v[:15]:
    print(f"  |v|={v:.3f}  {n:15s}  (v={vraw:+.3f})  [{pid}]")

print("\n=== NODOS INDICADORES TEMPRANOS (alta aceleracion + velocidad sostenida) ===\n")
for n in NODOS:
    acels = []
    for h in hitos:
        vel = h.get("velocidades", {}).get(n, {})
        acel = vel.get("aceleracion", 0) or 0
        vmedia = vel.get("media", 0)
        if abs(acel) > 0.1 and abs(vmedia) > 0.5:
            acels.append((acel, h["id"], vmedia))
    if len(acels) >= 2:
        dirs = set(a[2] >= 0 for a in acels)
        consistent = len(dirs) == 1
        print(f"  {'✓' if consistent else '?'} {n:15s}  {len(acels)} hitos  consistency={'same_dir' if consistent else 'mixed'}")
