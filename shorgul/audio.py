"""Tiny audio I/O helpers: everything is float32 mono at 16 kHz on disk as PCM16 wav."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

SR = 16000


def to_mono_16k(audio: np.ndarray, sr: int) -> np.ndarray:
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SR:
        g = np.gcd(sr, SR)
        audio = resample_poly(audio, SR // g, sr // g)
    return audio.astype(np.float32)


def read_wav(p: str | Path) -> np.ndarray:
    audio, sr = sf.read(str(p), dtype="float32", always_2d=False)
    return to_mono_16k(audio, sr)


def read_bytes(data: bytes) -> np.ndarray:
    audio, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
    return to_mono_16k(audio, sr)


def write_wav(p: str | Path, audio: np.ndarray) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(p), np.clip(audio, -1.0, 1.0), SR, subtype="PCM_16")
