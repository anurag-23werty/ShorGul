"""ffmpeg helpers: G.711 μ-law encode/decode round trip."""
from __future__ import annotations

import subprocess

import numpy as np


def ffmpeg_pipe(audio: np.ndarray, in_args: list[str], out_args: list[str]) -> bytes:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", *in_args, "-i", "pipe:0", *out_args, "pipe:1"]
    res = subprocess.run(cmd, input=audio.tobytes(), capture_output=True, check=True)
    return res.stdout


def mulaw_roundtrip_8k(audio_8k: np.ndarray) -> np.ndarray:
    """float32 8 kHz -> μ-law bytes -> float32 8 kHz."""
    f32 = ["-f", "f32le", "-ar", "8000", "-ac", "1"]
    ulaw = ffmpeg_pipe(audio_8k.astype(np.float32), f32, ["-c:a", "pcm_mulaw", "-f", "mulaw"])
    out = ffmpeg_pipe(np.frombuffer(ulaw, dtype=np.uint8), ["-f", "mulaw", "-ar", "8000", "-ac", "1"],
                      ["-f", "f32le"])
    return np.frombuffer(out, dtype=np.float32).copy()
