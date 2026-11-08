"""One-clip audit for the dashboard's "Try your audio" tab: health check + original and N conditions."""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
import soundfile as sf

from shorgul.asr.base import MockASR
from shorgul.asr.cache import Cache
from shorgul.asr.chunk import transcribe_any
from shorgul.asr.runner import params_for
from shorgul.audio import SR, read_bytes
from shorgul.audit.run import MOCK_TEXT
from shorgul.audit.stability import grade, stability
from shorgul.degrade.pipeline import degrade_audio, load_noises
from shorgul.entities.repair import repair
from shorgul.health.check import Health, check

CONDITIONS = ["phone", "loss_5", "traffic_5", "market_0"]
MAX_S = 600.0  # long calls are chunked at pauses (shorgul.asr.chunk)


@dataclass
class QuickResult:
    health: Health
    rows: list[dict]
    mean_stability: float
    grade: str
    billed_calls: int


def _wav_bytes(x: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.clip(x, -1, 1), SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def load_clip(data: bytes) -> np.ndarray:
    audio = read_bytes(data)
    if len(audio) / SR > MAX_S:
        raise ValueError(f"clip is {len(audio) / SR:.1f} s; the limit here is {MAX_S:.0f} s")
    return audio


def conditions_available(noises: dict) -> list[str]:
    return [c for c in CONDITIONS if not any(n in c for n in ("traffic", "market")) or noises]


def quick_audit(audio: np.ndarray, lang: str, model: str, mock: bool, key: str | None = None,
                backend=None, cache: Cache | None = None, noises: dict | None = None) -> QuickResult:
    """Billed calls = 1 + len(conditions) minus cache hits; mock never bills."""
    noises = load_noises() if noises is None else noises
    conds = conditions_available(noises)
    if backend is None:
        if mock:
            backend = MockASR(model)
        else:
            from shorgul.asr.prisma import PrismaASR
            backend = PrismaASR(model, key=key)
    cache = cache or Cache.default(mock)
    params = params_for(model, {"lang": lang, "has_entities": lang.startswith("hinglish")}, "raw")
    rows, billed = [], 0
    for cond in ["original", *conds]:
        x = audio if cond == "original" else degrade_audio(audio, "upload", cond, noises)[0]
        text, status, n = transcribe_any(x, backend, model, params, cache,
                                         {"_reference": MOCK_TEXT, "_variant": "raw",
                                          "_condition": "clean" if cond == "original" else cond})
        billed += n
        rows.append({"condition": cond, "transcript": text, "repaired": repair(text), "status": status,
                     "audio": _wav_bytes(x)})
    orig = rows[0]["transcript"]
    for r in rows[1:]:
        r["stability"] = stability(orig, r["transcript"], lang)
    mean_s = float(np.mean([r["stability"] for r in rows[1:]])) if len(rows) > 1 else 0.0
    return QuickResult(check(audio), rows, mean_s, grade(mean_s), billed)
