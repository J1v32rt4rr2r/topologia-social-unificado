from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _ruta_config() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "config" / "nodos.yaml"


def cargar_combinaciones() -> list[dict]:
    """Lee la sección `combinaciones_nodos` de config/nodos.yaml.

    Combinaciones = pares de nodos culturales con frases de búsqueda
    curadas (intersecciones), p. ej. "política económica", "educación sexual".
    """
    ruta = _ruta_config()
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return list(data.get("combinaciones_nodos", []))


def frases_para_nodo(nodo_id: str, max_frases: int | None = None) -> list[str]:
    """Frases de todas las combinaciones que involucran a `nodo_id`, sin duplicados."""
    frases: list[str] = []
    vistos: set[str] = set()
    for combo in cargar_combinaciones():
        if nodo_id not in combo.get("nodos", []):
            continue
        for frase in combo.get("frases", []):
            if frase and frase not in vistos:
                vistos.add(frase)
                frases.append(frase)
    if max_frases is not None:
        frases = frases[:max_frases]
    return frases


def frases_para_pareja(nodo_a: str, nodo_b: str) -> list[str]:
    for combo in cargar_combinaciones():
        nodos = combo.get("nodos", [])
        if nodo_a in nodos and nodo_b in nodos:
            return list(combo.get("frases", []))
    return []


def actualizar_termino(termino: str) -> str:
    """Sesga la búsqueda hacia noticias recientes y Chile.

    'política económica' → 'política económica Chile noticias agosto 2026'.
    Idempotente: no duplica 'Chile' ni el sufijo si ya están presentes.
    """
    hoy = datetime.now()
    sufijo = f"noticias {_MESES[hoy.month - 1]} {hoy.year}"
    texto = termino.strip()
    if "Chile" not in texto:
        texto = f"{texto} Chile"
    if sufijo not in texto:
        texto = f"{texto} {sufijo}"
    return texto
