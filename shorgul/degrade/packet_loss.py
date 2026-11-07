"""Random packet loss: drop (zero) whole 20 ms frames with probability `rate`."""
from __future__ import annotations

import numpy as np


def apply_packet_loss(audio: np.ndarray, rate: float, rng: np.random.Generator,
                      frame_ms: int = 20, sr: int = 16000) -> tuple[np.ndarray, float]:
    """Return (audio with lost frames zeroed, fraction of frames lost)."""
    flen = sr * frame_ms // 1000
    n_frames = int(np.ceil(len(audio) / flen))
    lost = rng.random(n_frames) < rate
    out = audio.copy()
    for i in np.flatnonzero(lost):
        out[i * flen:(i + 1) * flen] = 0.0
    return out, float(lost.mean()) if n_frames else 0.0
