"""SQLite cache for every billed call (ASR responses and TTS audio)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from shorgul.config import path


def asr_key(audio: bytes, model: str, params: dict[str, Any]) -> str:
    h = hashlib.sha256(audio)
    h.update(model.encode())
    h.update(json.dumps(params, sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()


class Cache:
    def __init__(self, db: Path) -> None:
        db.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db))
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS asr (key TEXT PRIMARY KEY, model TEXT, params TEXT,"
            " response TEXT, status TEXT, latency_s REAL, created REAL)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS blobs (key TEXT PRIMARY KEY, data BLOB, created REAL)")
        self.conn.commit()

    @classmethod
    def default(cls, mock: bool = False) -> "Cache":
        base = path("results") / ("mock" if mock else "")
        return cls(base / "cache.sqlite")

    def get(self, key: str) -> dict | None:
        row = self.conn.execute(
            "SELECT response, status, latency_s FROM asr WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        return {"response": json.loads(row[0]), "status": row[1], "latency_s": row[2]}

    def put(self, key: str, model: str, params: dict, response: dict, status: str, latency_s: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO asr VALUES (?,?,?,?,?,?,?)",
            (key, model, json.dumps(params, ensure_ascii=False), json.dumps(response, ensure_ascii=False),
             status, latency_s, time.time()))
        self.conn.commit()

    def get_blob(self, key: str) -> bytes | None:
        row = self.conn.execute("SELECT data FROM blobs WHERE key=?", (key,)).fetchone()
        return None if row is None else bytes(row[0])

    def put_blob(self, key: str, data: bytes) -> None:
        self.conn.execute("INSERT OR REPLACE INTO blobs VALUES (?,?,?)", (key, data, time.time()))
        self.conn.commit()
