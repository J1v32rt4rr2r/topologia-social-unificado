from __future__ import annotations

from pathlib import Path

import yaml

from topologia.models.schemas import EstadoCultural, ItemInformativo

NODOS_CULTURALES = [
    "ECONOMIA", "TRABAJO", "CONTINUIDAD", "POLITICA",
    "LENGUAJE", "ETICA_ESTETICA", "TECNOLOGIA", "EDUCACION", "RELIGION",
]

UMBRAL_ITEMS_MINIMOS = 3
UMBRAL_SCORE_PLANO = 0.5

UMBRAL_POR_NODO: dict[str, int] = {
    "RELIGION": 1,
}


def _cargar_palabras_clave() -> dict:
    ruta = Path(__file__).resolve().parent.parent.parent.parent / "config" / "palabras_clave.yaml"
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


_PALABRAS_CACHE: dict | None = None


def _obtener_palabras_clave() -> dict:
    global _PALABRAS_CACHE
    if _PALABRAS_CACHE is None:
        _PALABRAS_CACHE = _cargar_palabras_clave()
    return _PALABRAS_CACHE


def terminos_para_nodo(nodo_id: str) -> list[str]:
    data = _obtener_palabras_clave()
    nodos = data.get("nodos", {})
    info = nodos.get(nodo_id, {})
    return info.get("clasificacion", [nodo_id.lower()])


def clasificar_items_por_nodo_semantico(
    items: list[ItemInformativo],
) -> dict[str, list[ItemInformativo]]:
    mapa: dict[str, list[ItemInformativo]] = {}
    for nodo_id in NODOS_CULTURALES:
        terminos = terminos_para_nodo(nodo_id)
        encontrados: list[ItemInformativo] = []
        for it in items:
            texto = (it.titulo + " " + it.contenido).lower()
            if any(t in texto for t in terminos):
                encontrados.append(it)
        umbral = UMBRAL_POR_NODO.get(nodo_id, UMBRAL_ITEMS_MINIMOS)
        mapa[nodo_id] = encontrados or items[:umbral]
    return mapa


def detectar_brechas(
    estado: EstadoCultural | None,
    items_por_nodo: dict[str, list[ItemInformativo]] | None = None,
) -> dict[str, dict]:
    brechas: dict[str, dict] = {}
    hay_items = items_por_nodo is not None

    if hay_items:
        for nodo_id in NODOS_CULTURALES:
            items_nodo = items_por_nodo.get(nodo_id, [])
            reales = [it for it in items_nodo if _es_item_relevante(it, nodo_id)]
            umbral = UMBRAL_POR_NODO.get(nodo_id, UMBRAL_ITEMS_MINIMOS)
            brechas[nodo_id] = {
                "total_items": len(items_nodo),
                "items_relevantes": len(reales),
                "tiene_brecha": len(reales) < umbral,
            }

    if estado:
        for n in estado.nodos:
            if n.nodo_id not in brechas:
                brechas[n.nodo_id] = {"total_items": 0, "items_relevantes": 0, "tiene_brecha": True}
            brechas[n.nodo_id]["dimension_m"] = n.dimension_m
            brechas[n.nodo_id]["dimension_l"] = n.dimension_l
            brechas[n.nodo_id]["dimension_s"] = n.dimension_s
            brechas[n.nodo_id]["delta"] = round(n.delta, 1)
            brechas[n.nodo_id]["fragil"] = n.fragil
            brechas[n.nodo_id]["score_plano"] = (
                n.dimension_m == 5.0 and n.dimension_l == 5.0 and n.dimension_s == 5.0
            )

    if not hay_items:
        brechas["_meta"] = {"modo": "standalone", "mensaje": "Sin datos de items (solo estado)"}

    return brechas


def _es_item_relevante(item: ItemInformativo, nodo_id: str) -> bool:
    terminos = terminos_para_nodo(nodo_id)
    texto = (item.titulo + " " + item.contenido).lower()
    return any(t in texto for t in terminos)


def resumen_brechas(brechas: dict[str, dict]) -> str:
    partes: list[str] = []
    contadores = {"con_datos": 0, "sin_datos": 0, "score_plano": 0}
    for nid, info in brechas.items():
        if info.get("score_plano"):
            contadores["score_plano"] += 1
            contadores["sin_datos"] += 1
        elif info.get("tiene_brecha"):
            contadores["sin_datos"] += 1
        else:
            contadores["con_datos"] += 1
    partes.append(f"{contadores['con_datos']}/9 nodos con datos suficientes")
    if contadores["score_plano"]:
        planos = [nid for nid, info in brechas.items() if info.get("score_plano")]
        partes.append(f"{contadores['score_plano']} nodos sin datos: {', '.join(planos)}")
    return " | ".join(partes)
