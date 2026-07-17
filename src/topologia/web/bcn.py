from __future__ import annotations

from datetime import datetime

from topologia.models.schemas import ItemInformativo


BCN_URLS = [
    ("https://www.bcn.cl/leychile", "leyes"),
    ("https://www.bcn.cl/siit", "territorio"),
    ("https://www.bcn.cl/catalogos", "catalogos"),
]


CATEGORIA_NODOS = {
    "leyes": "POLITICA",
    "territorio": "CONTINUIDAD",
    "catalogos": "EDUCACION",
}


def obtener_items(limite: int = 5) -> list[ItemInformativo]:
    items: list[ItemInformativo] = []
    for url, categoria in BCN_URLS[:limite]:
        node = CATEGORIA_NODOS.get(categoria, "POLITICA")
        items.append(ItemInformativo(
            id=f"bcn-{len(items)}",
            titulo=f"BCN: {categoria.capitalize()}",
            fuente="bcn",
            contenido=f"Recurso de la Biblioteca del Congreso Nacional. Categoría: {categoria}.",
            url=url,
            fecha=datetime.now(),
            tags=["bcn", categoria, node],
        ))
    return items
