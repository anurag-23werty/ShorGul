"""ASR interface + deterministic mock backend (for testing the pipeline without credits)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np


@dataclass
class ASRResult:
    transcript: str
    status: str            # ok | ok_truncated | error_<code> | rate_limited | failed
    latency_s: float
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def cacheable(self) -> bool:
        # deterministic outcomes only: success, or a 4xx the server will always return
        return self.status.startswith("ok") or self.status.startswith("error_4")


class ASRBackend(Protocol):
    name: str
    billed: bool

    def transcribe(self, audio: bytes, params: dict[str, Any]) -> ASRResult: ...


# How hard each condition is for the mock (fraction of words corrupted)
MOCK_SEVERITY = {"clean": 0.04, "phone": 0.08, "loss_5": 0.16, "traffic_10": 0.12,
                 "traffic_5": 0.2, "market_10": 0.18, "market_0": 0.4}
MOCK_MODEL = {"prisma-v3.0": 0.8, "prisma-v2.5": 1.0, "whisper-small": 1.6}
MOCK_VARIANT = {"raw": 1.0, "denoised": 0.9, "context": 0.7}


class MockASR:
    """Returns the reference with seeded word drops/substitutions scaled by condition difficulty."""
    billed = False

    def __init__(self, name: str) -> None:
        self.name = name

    def transcribe(self, audio: bytes, params: dict[str, Any]) -> ASRResult:
        ref: str = params["_reference"]
        rate = min(0.95, MOCK_SEVERITY.get(params["_condition"], 0.1)
                   * MOCK_MODEL.get(self.name, 1.0) * MOCK_VARIANT.get(params["_variant"], 1.0))
        seed = int(hashlib.sha256(audio + self.name.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        out = []
        for w in ref.split():
            r = rng.random()
            if r < rate / 2:
                continue                      # deletion
            out.append(w[::-1] if r < rate else w)  # substitution
        return ASRResult(" ".join(out), "ok", round(0.2 + 0.05 * rng.random(), 3), {"mock": True})
