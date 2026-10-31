"""Caricamento configurazione e costruzione delle fonti (importa gli adapter)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from core.http import PoliteClient
from . import base  # noqa: F401
from . import direct, shopify  # noqa: F401  (registrano gli adapter)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"


def load_yaml(name: str) -> Dict[str, Any]:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_sources(config: Dict[str, Any], client: PoliteClient) -> List[base.Source]:
    defaults = config.get("defaults", {})
    sources: List[base.Source] = []
    for entry in config.get("sources", []):
        if not entry.get("enabled", True):
            continue
        merged = {**defaults, **entry}
        sources.append(base.build_source(merged, client))
    return sources
