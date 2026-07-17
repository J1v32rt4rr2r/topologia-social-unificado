from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import yaml

from topologia.models.schemas import EstadoCultural, PatronAnalogico


class FileStore:
    def __init__(self, data_dir: str | None = None):
        if data_dir:
            self.base = Path(data_dir)
        else:
            self.base = Path.home() / ".local" / "share" / "topologia-social" / "data"
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / "estados").mkdir(exist_ok=True)
        (self.base / "estudios").mkdir(exist_ok=True)
        (self.base / "proyecciones").mkdir(exist_ok=True)
        (self.base / "memoria").mkdir(exist_ok=True)

    def guardar_json(self, ruta: str, data: dict) -> None:
        archivo = self.base / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def cargar_json(self, ruta: str) -> dict | None:
        archivo = self.base / ruta
        if not archivo.exists():
            return None
        return json.loads(archivo.read_text(encoding="utf-8"))

    def guardar_yaml(self, ruta: str, data: dict) -> None:
        archivo = self.base / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    def guardar_estado(self, estado: EstadoCultural) -> None:
        fecha = estado.fecha.strftime("%Y-%m-%d")
        self.guardar_json(f"estados/{estado.sociedad}_{fecha}.json", estado.model_dump(mode="json"))

    def cargar_estado(self, sociedad: str, fecha: str | None = None) -> EstadoCultural | None:
        if fecha:
            data = self.cargar_json(f"estados/{sociedad}_{fecha}.json")
        else:
            archivos = sorted((self.base / "estados").glob(f"{sociedad}_*.json"))
            if not archivos:
                return None
            data = json.loads(archivos[-1].read_text(encoding="utf-8"))
        if data:
            return EstadoCultural(**data)
        return None

    def listar_estados(self, sociedad: str) -> list[str]:
        archivos = sorted((self.base / "estados").glob(f"{sociedad}_*.json"))
        return [a.stem.split("_", 1)[1] for a in archivos]

    def guardar_patron(self, patron: PatronAnalogico) -> None:
        ruta = self.base / "memoria" / "patrones.json"
        existentes = []
        if ruta.exists():
            existentes = json.loads(ruta.read_text(encoding="utf-8"))
        existentes = [p for p in existentes if p["id"] != patron.id]
        existentes.append(patron.model_dump(mode="json"))
        ruta.write_text(json.dumps(existentes, indent=2, default=str), encoding="utf-8")

    def cargar_patrones(self) -> list[PatronAnalogico]:
        ruta = self.base / "memoria" / "patrones.json"
        if not ruta.exists():
            return []
        data = json.loads(ruta.read_text(encoding="utf-8"))
        return [PatronAnalogico(**p) for p in data]

    def existe(self, ruta: str) -> bool:
        return (self.base / ruta).exists()

    def listar(self, subdir: str) -> list[str]:
        directorio = self.base / subdir
        if not directorio.exists():
            return []
        return [str(a.relative_to(self.base)) for a in directorio.iterdir() if a.is_file()]
