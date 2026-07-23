from __future__ import annotations

from datetime import datetime

import requests

from topologia.logger import logger
from topologia.models.schemas import ItemInformativo


GUTENDEX_API = "https://gutendex.com/books"
USER_AGENT = (
    "TopologiaSocial/2.0 "
    "(Proyecto de investigacion sociologica; "
    "monitoreo de clima cultural chileno; "
    "https://github.com/J1v32rt4rr2r/topologia-social-unificado; "
    "contacto: j1v32rt4rr2r@proton.me)"
)
TIMEOUT = 15


AUTORES_CLASICOS = [
    "César Vallejo",
    "Rubén Darío",
    "Sor Juana Inés de la Cruz",
    "Pablo Neruda",
    "Gabriela Mistral",
    "Alfonsina Storni",
    "Jorge Luis Borges",
    "Federico García Lorca",
    "Antonio Machado",
    "Octavio Paz",
]


def listar_autores() -> list[str]:
    return list(AUTORES_CLASICOS)


def _buscar_en_gutendex(query: str, max_results: int = 5) -> list[dict]:
    params = {"search": query}
    try:
        resp = requests.get(GUTENDEX_API, params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])[:max_results]
    except requests.RequestException as e:
        logger.warning(f"Gutendex error buscando '{query}': {e}")
        return []
    except ValueError as e:
        logger.warning(f"Gutendex JSON inválido para '{query}': {e}")
        return []


def buscar_autores(query: str) -> list[ItemInformativo]:
    items: list[ItemInformativo] = []
    for autor in AUTORES_CLASICOS:
        if query.lower() in autor.lower():
            libros = _buscar_en_gutendex(autor)
            if libros:
                for libro in libros:
                    titulo = libro.get("title", autor)
                    items.append(ItemInformativo(
                        id=f"gutenberg-{len(items)}",
                        titulo=titulo,
                        fuente="gutenberg",
                        contenido=f"Libro de {autor}. Descarga: {libro.get('formats', {}).get('text/html', '')}",
                        url=libro.get("formats", {}).get("text/html", f"https://www.gutenberg.org/ebooks/{libro.get('id', '')}"),
                        fecha=datetime.now(),
                        tags=["poesia", autor.lower().replace(" ", "_"), "gutenberg"],
                    ))
            else:
                items.append(ItemInformativo(
                    id=f"gutenberg-{len(items)}",
                    titulo=autor,
                    fuente="gutenberg",
                    contenido=f"Poeta clásico. No se encontraron libros en Gutenberg.",
                    url=f"https://www.gutenberg.org/ebooks/search/?query={requests.utils.quote(autor)}",
                    fecha=datetime.now(),
                    tags=["poesia", autor.lower().replace(" ", "_"), "gutenberg"],
                ))
    return items


def obtener_poema_del_dia() -> ItemInformativo | None:
    import random
    autor = random.choice(AUTORES_CLASICOS)
    libros = _buscar_en_gutendex(autor, max_results=3)
    if libros:
        libro = libros[0]
        return ItemInformativo(
            id="poema-diario",
            titulo=libro.get("title", f"Poema del día - {autor}"),
            fuente="gutenberg",
            contenido=f"Lectura sugerida: {libro.get('title', '')} de {autor}. Descarga: {libro.get('formats', {}).get('text/html', '')}",
            url=libro.get("formats", {}).get("text/html", f"https://www.gutenberg.org/ebooks/{libro.get('id', '')}"),
            fecha=datetime.now(),
            tags=["poesia", "diario", autor.lower().replace(" ", "_"), "gutenberg"],
        )
    return ItemInformativo(
        id="poema-diario",
        titulo=f"Poema del día - {autor}",
        fuente="gutenberg",
        contenido=f"Lectura sugerida: explorar obra de {autor} en https://www.gutenberg.org",
        url=f"https://www.gutenberg.org/ebooks/search/?query={requests.utils.quote(autor)}",
        fecha=datetime.now(),
        tags=["poesia", "diario", autor.lower().replace(" ", "_"), "gutenberg"],
    )
