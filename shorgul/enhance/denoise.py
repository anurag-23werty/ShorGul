"""Server-side fix #1: non-stationary spectral gating (noisereduce) on the received phone audio."""
from __future__ import annotations

import numpy as np
import noisereduce as nr
import pandas as pd

from shorgul.audio import SR, read_wav, write_wav
from shorgul.config import path


def denoise(audio: np.ndarray) -> np.ndarray:
    out = nr.reduce_noise(y=audio, sr=SR, stationary=False, prop_decrease=0.9)
    return np.asarray(out, dtype=np.float32)


def enhance_all(manifest: pd.DataFrame, conditions: list[str], force: bool = False) -> int:
    n = 0
    for clip_id in manifest["clip_id"]:
        for cond in conditions:
            src = path("degraded") / cond / f"{clip_id}.wav"
            dst = path("enhanced") / cond / f"{clip_id}.wav"
            if not src.exists() or (dst.exists() and not force):
                continue
            write_wav(dst, denoise(read_wav(src)))
            n += 1
    return n
