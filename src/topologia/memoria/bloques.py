from __future__ import annotations

from pathlib import Path

from topologia.paths import get_memoria_dir


class BloquesMemoria:
    def __init__(self, ruta: str | None = None):
        if ruta:
            self.base = Path(ruta)
        else:
            self.base = get_memoria_dir() / "bloques"
        self.base.mkdir(parents=True, exist_ok=True)

    def _ruta(self, nombre: str) -> Path:
        return self.base / f"{nombre}.md"

    def leer(self, nombre: str) -> str:
        ruta = self._ruta(nombre)
        if ruta.exists():
            return ruta.read_text(encoding="utf-8")
        return ""

    def escribir(self, nombre: str, contenido: str):
        self._ruta(nombre).write_text(contenido, encoding="utf-8")

    def listar(self) -> list[str]:
        return [a.stem for a in self.base.glob("*.md")]

    def resumen(self) -> dict[str, str]:
        resumen = {}
        for nombre in self.listar():
            contenido = self.leer(nombre)
            resumen[nombre] = contenido[:200] + "..." if len(contenido) > 200 else contenido
        return resumen
