from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from topologia.models.schemas import PatronAnalogico
from topologia.paths import get_memoria_dir


TIPOS_DECISION = ("preference", "decision", "pattern", "lesson", "observation")


class DecisionDB:
    def __init__(self, ruta: str | None = None):
        if ruta:
            self.ruta = Path(ruta)
        else:
            self.ruta = get_memoria_dir()
        self.ruta.mkdir(parents=True, exist_ok=True)
        self._archivo = self.ruta / "decisions.json"
        self._patrones = self.ruta / "patrones.json"
        self._decisiones: list[dict] = []
        self._cargar()

    def _cargar(self):
        if self._archivo.exists():
            self._decisiones = json.loads(self._archivo.read_text(encoding="utf-8"))
        else:
            self._decisiones = []

    def _guardar(self):
        self._archivo.write_text(
            json.dumps(self._decisiones, indent=2, default=str),
            encoding="utf-8",
        )

    def registrar(self, tipo: str, contenido: str, tags: list[str] | None = None):
        if tipo not in TIPOS_DECISION:
            raise ValueError(f"Tipo inválido: {tipo}. Válidos: {TIPOS_DECISION}")
        entry = {
            "id": f"dec-{len(self._decisiones) + 1:04d}",
            "tipo": tipo,
            "contenido": contenido,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat(),
        }
        self._decisiones.append(entry)
        self._guardar()
        return entry["id"]

    def listar(self, tipo: str | None = None, tag: str | None = None) -> list[dict]:
        resultados = self._decisiones
        if tipo:
            resultados = [d for d in resultados if d["tipo"] == tipo]
        if tag:
            resultados = [d for d in resultados if tag in d.get("tags", [])]
        return resultados

    def patrones(self) -> list[PatronAnalogico]:
        if not self._patrones.exists():
            return []
        data = json.loads(self._patrones.read_text(encoding="utf-8"))
        return [PatronAnalogico(**p) for p in data]

    def guardar_patron(self, patron: PatronAnalogico):
        existentes = self.patrones()
        existentes = [p for p in existentes if p.id != patron.id]
        existentes.append(patron)
        self._patrones.write_text(
            json.dumps([p.model_dump(mode="json") for p in existentes], indent=2, default=str),
            encoding="utf-8",
        )

    def patron_por_id(self, patron_id: str) -> PatronAnalogico | None:
        for p in self.patrones():
            if p.id == patron_id:
                return p
        return None

    def sincronizar_desde(self, ruta_externa: str):
        ext = Path(ruta_externa)
        if ext.exists():
            data = json.loads(ext.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._decisiones = data
                self._guardar()

    def estadisticas(self) -> dict:
        total = len(self._decisiones)
        por_tipo = {}
        for d in self._decisiones:
            t = d["tipo"]
            por_tipo[t] = por_tipo.get(t, 0) + 1
        return {
            "total": total,
            "por_tipo": por_tipo,
            "patrones": len(self.patrones()),
            "estudios_totales": sum(p.veces_estudiado for p in self.patrones()),
        }
