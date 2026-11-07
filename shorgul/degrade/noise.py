"""Additive background noise at a target SNR (speech power over active frames only)."""
from __future__ import annotations

import numpy as np


def active_power(x: np.ndarray, sr: int = 16000, frame_ms: int = 20, gate_db: float = -40.0) -> float:
    """Mean power of frames within `gate_db` of the loudest frame (ignores leading/trailing silence)."""
    flen = sr * frame_ms // 1000
    n = len(x) // flen
    if n == 0:
        return float(np.mean(x**2))
    p = np.mean(x[: n * flen].reshape(n, flen) ** 2, axis=1)
    active = p >= p.max() * 10 ** (gate_db / 10)
    return float(p[active].mean())


def noise_segment(noise: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Loop if too short, then crop n samples from a seeded random offset."""
    if len(noise) < n:
        noise = np.tile(noise, int(np.ceil(n / len(noise))) + 1)
    start = int(rng.integers(0, len(noise) - n + 1))
    return noise[start:start + n]


def mix_at_snr(speech: np.ndarray, noise: np.ndarray, snr_db: float,
               rng: np.random.Generator, peak: float = 0.99) -> np.ndarray:
    seg = noise_segment(noise, len(speech), rng)
    p_speech = active_power(speech)
    p_noise = float(np.mean(seg**2)) + 1e-12
    scale = np.sqrt(p_speech / (p_noise * 10 ** (snr_db / 10)))
    mix = speech + scale * seg
    m = float(np.abs(mix).max())
    if m > peak:  # scale both together -> SNR unchanged, no clipping
        mix *= peak / m
    return mix.astype(np.float32)
