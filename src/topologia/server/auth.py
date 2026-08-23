"""Autenticación del servidor web.

Protege los endpoints que ejecutan ciclos LLM costosos o leen archivos
arbitrarios. El cliente debe enviar el header `X-API-Key` con el valor de
`API_AUTH_KEY` (ver .env.example). Si `API_AUTH_KEY` no está configurada,
el endpoint rechaza la petición: falla cerrada en lugar de quedar abierta.
"""

from __future__ import annotations

import os

from fastapi import Header, HTTPException


def requerir_api_key(x_api_key: str | None = Header(default=None)) -> None:
    clave = os.getenv("API_AUTH_KEY", "").strip()
    if not clave:
        raise HTTPException(
            status_code=503,
            detail="API_AUTH_KEY no está configurada en .env; el endpoint queda bloqueado por seguridad",
        )
    if x_api_key != clave:
        raise HTTPException(
            status_code=401,
            detail="API key inválida (header X-API-Key requerido)",
        )
