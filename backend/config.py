"""
First-run configuration, persisted to data/config.json.
Stores the path to the user's lecture material folder + indexing metadata.
"""
import json
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path(__file__).parent.parent / "data" / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def save_config(data: dict) -> dict:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = load_config()
    existing.update(data)
    CONFIG_PATH.write_text(json.dumps(existing, indent=2))
    return existing


def is_first_run() -> bool:
    cfg = load_config()
    return not cfg.get("materials_path")


def get_materials_path() -> Optional[str]:
    return load_config().get("materials_path")
