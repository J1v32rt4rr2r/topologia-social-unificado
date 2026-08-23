"""Configuración común de pytest.

Congela el reloj (15 de agosto de 2026) en los módulos que construyen
búsquedas con mes/año actuales. Sin esto, los tests que asertan cadenas como
"noticias agosto 2026" (generadas con `datetime.now()`) fallarían al cambiar
de mes o de año, y los que dependen del año actual (p. ej. la agenda del INE)
se romperían en 2027.
"""

from __future__ import annotations

from datetime import datetime

import pytest


class _FechaCongelada(datetime):
    """Subclase de datetime con now() fijo; conserva el resto del comportamiento."""

    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 8, 15, 6, 0, 0, tzinfo=tz)


_MODULOS_CON_RELOJ = [
    "topologia.web.compuestos",
    "topologia.web.relevancia",
    "topologia.web.scraping",
    "topologia.web.ine",
    "topologia.web.tendencias",
    "topologia.web.bcentral",
    "topologia.web.rss",
    "topologia.web.search",
    "topologia.web.descubridor",
    "topologia.web.analizador",
]


@pytest.fixture(autouse=True)
def _congelar_reloj(monkeypatch):
    for nombre in _MODULOS_CON_RELOJ:
        monkeypatch.setattr(f"{nombre}.datetime", _FechaCongelada, raising=False)
