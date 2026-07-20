from __future__ import annotations

from pathlib import Path


def get_data_dir() -> Path:
    return Path.home() / ".local" / "share" / "topologia-social" / "data"


def get_memoria_dir() -> Path:
    return get_data_dir() / "memoria"


def get_reportes_dir() -> Path:
    return get_data_dir() / "reportes"


def get_estados_dir() -> Path:
    return get_data_dir() / "estados"
