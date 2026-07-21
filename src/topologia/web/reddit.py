"""
Módulo de consulta a Reddit vía PRAW (read-only) para obtener posts
del subreddit r/chile como parte de la Fase 4 (discursiva de masas).

Requiere credenciales de app Reddit en .env:
  REDDIT_CLIENT_ID=xxx
  REDDIT_CLIENT_SECRET=xxx
(Crear app gratuita en: https://www.reddit.com/prefs/apps -> "script")

Se limita a metadato público: título, puntuación, número de comentarios,
sin incluir nombres de usuario ni datos personales.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from topologia.logger import logger
from topologia.models.schemas import ItemInformativo

load_dotenv()

USER_AGENT = (
    "TopologiaSocial/2.0 "
    "(Proyecto de investigacion sociologica; "
    "monitoreo de clima cultural chileno; "
    "https://github.com/J1v32rt4rr2r/topologia-social-unificado; "
    "contacto: j1v32rt4rr2r@proton.me)"
)

_ultima_llamada: float = 0.0
_DELAY = 2.0


def _esperar() -> None:
    global _ultima_llamada
    ahora = time.time()
    diff = ahora - _ultima_llamada
    if diff < _DELAY:
        time.sleep(_DELAY - diff)
    _ultima_llamada = time.time()


def obtener_posts(
    subreddit: str = "chile",
    seccion: str = "hot",
    max_resultados: int = 25,
) -> list[ItemInformativo]:
    """
    Obtiene posts del subreddit chileno usando PRAW (read-only).

    Args:
        subreddit: Subreddit a consultar (default "chile").
        seccion: "hot" | "new" | "top" (default "hot").
        max_resultados: Máximo de posts (default 25).

    Returns:
        Lista de ItemInformativo con título, puntuación, URL.
    """
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        logger.warning(
            "Reddit: credenciales no configuradas. "
            "Agregar REDDIT_CLIENT_ID y REDDIT_CLIENT_SECRET en .env "
            "(https://www.reddit.com/prefs/apps)"
        )
        return []

    try:
        import praw
    except ImportError:
        logger.error("praw no instalado: pip install praw")
        return []

    try:
        _esperar()
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=USER_AGENT,
        )
        sub = reddit.subreddit(subreddit)

        metodo = getattr(sub, seccion, sub.hot)
        resultados: list[ItemInformativo] = []

        for i, post in enumerate(metodo(limit=max_resultados)):
            if i >= max_resultados:
                break
            contenido = f"[{post.score} pts | {post.num_comments} comentarios]"
            if post.selftext:
                contenido += f" {post.selftext[:500]}"

            resultados.append(ItemInformativo(
                id=f"reddit-{subreddit}-{i}",
                titulo=post.title or "",
                fuente=f"reddit/r/{subreddit}",
                contenido=contenido,
                url=f"https://www.reddit.com{post.permalink}" if post.permalink else "",
                fecha=datetime.fromtimestamp(post.created_utc, tz=timezone.utc) if post.created_utc else datetime.now(timezone.utc),
                tags=["reddit", subreddit, seccion],
            ))

        logger.info(f"Reddit r/{subreddit}/{seccion}: {len(resultados)} posts")
        return resultados

    except Exception as e:
        logger.error(f"Reddit error: {e}")
        return []
