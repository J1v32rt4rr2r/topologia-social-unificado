from __future__ import annotations

from datetime import datetime

from topologia.models.schemas import ItemInformativo


AUTORES_CLASICOS = {
    "César Vallejo": "https://www.gutenberg.org/ebooks/search/?query=C%C3%A9sar+Vallejo",
    "Rubén Darío": "https://www.gutenberg.org/ebooks/search/?query=Rub%C3%A9n+Dar%C3%ADo",
    "Sor Juana Inés de la Cruz": "https://www.gutenberg.org/ebooks/search/?query=Sor+Juana+In%C3%A9s+de+la+Cruz",
    "Pablo Neruda": "https://www.gutenberg.org/ebooks/search/?query=Pablo+Neruda",
    "Gabriela Mistral": "https://www.gutenberg.org/ebooks/search/?query=Gabriela+Mistral",
    "Alfonsina Storni": "https://www.gutenberg.org/ebooks/search/?query=Alfonsina+Storni",
}


def listar_autores() -> list[str]:
    return list(AUTORES_CLASICOS.keys())


def buscar_autores(query: str) -> list[ItemInformativo]:
    items: list[ItemInformativo] = []
    for autor, url in AUTORES_CLASICOS.items():
        if query.lower() in autor.lower():
            items.append(ItemInformativo(
                id=f"poet-{len(items)}",
                titulo=autor,
                fuente="gutenberg",
                contenido=f"Poeta clásico. Búsqueda en: {url}",
                url=url,
                fecha=datetime.now(),
                tags=["poesia", autor.lower().replace(" ", "_")],
            ))
    return items


def obtener_poema_del_dia() -> ItemInformativo | None:
    import random
    autores = list(AUTORES_CLASICOS.keys())
    if not autores:
        return None
    autor = random.choice(autores)
    return ItemInformativo(
        id="poema-diario",
        titulo=f"Poema del día - {autor}",
        fuente="gutenberg",
        contenido=f"Lectura sugerida: explorar obra de {autor}",
        url=AUTORES_CLASICOS[autor],
        fecha=datetime.now(),
        tags=["poesia", "diario", autor.lower().replace(" ", "_")],
    )
