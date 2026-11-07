"""Narrowband phone channel: 300–3400 Hz bandpass -> 8 kHz -> μ-law -> back to 16 kHz."""
from __future__ import annotations

import numpy as np

from shorgul.degrade.codecs import ffmpeg_pipe, mulaw_roundtrip_8k


def _fit(x: np.ndarray, n: int) -> np.ndarray:
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))


def phone_channel(audio: np.ndarray, low_hz: int = 300, high_hz: int = 3400, rate: int = 8000) -> np.ndarray:
    f32_16k = ["-f", "f32le", "-ar", "16000", "-ac", "1"]
    # two cascaded 2-pole filters per edge ≈ 4th-order skirts, like a real handset/line response
    bp = f"highpass=f={low_hz},highpass=f={low_hz},lowpass=f={high_hz},lowpass=f={high_hz}"
    nb = ffmpeg_pipe(audio.astype(np.float32), f32_16k, ["-af", bp, "-ar", str(rate), "-f", "f32le"])
    nb = mulaw_roundtrip_8k(np.frombuffer(nb, dtype=np.float32))
    up = ffmpeg_pipe(nb, ["-f", "f32le", "-ar", str(rate), "-ac", "1"], ["-ar", "16000", "-f", "f32le"])
    return _fit(np.frombuffer(up, dtype=np.float32).copy(), len(audio))
