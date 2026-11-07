"""Config loading, project paths, deterministic seeding."""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "bench.yaml"


@lru_cache(maxsize=1)
def load_config(path: str | None = None) -> dict[str, Any]:
    with open(path or CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def path(key: str) -> Path:
    """Absolute path for a key under `paths:` in bench.yaml."""
    return ROOT / load_config()["paths"][key]


def seed_for(clip_id: str, condition: str) -> int:
    """Stable 32-bit seed. (Python's hash() is salted per process, so not used.)"""
    digest = hashlib.sha256(f"{clip_id}|{condition}".encode()).hexdigest()
    return int(digest[:8], 16)


def api_key() -> str:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("GNANI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GNANI_API_KEY is not set (put it in .env)")
    return key
