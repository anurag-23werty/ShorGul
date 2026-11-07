"""Download DEMAND ambience (Zenodo 1227121, CC BY-SA 3.0) and build traffic.wav / market.wav."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import requests

from shorgul.audio import read_bytes, write_wav

ZENODO = "https://zenodo.org/records/1227121/files/{name}_16k.zip?download=1"
# market = public square + cafeteria babble (closest DEMAND match to a busy bazaar)
RECIPES = {"traffic": ["STRAFFIC"], "market": ["SPSQUARE", "PCAFETER"]}


def _channel1(env: str) -> np.ndarray:
    r = requests.get(ZENODO.format(name=env), timeout=300)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name = next(n for n in z.namelist() if n.endswith("ch01.wav"))
        return read_bytes(z.read(name))


def _rms_norm(x: np.ndarray) -> np.ndarray:
    return x / (np.sqrt(np.mean(x**2)) + 1e-12) * 0.05


def fetch_noise(out_dir: Path) -> list[Path]:
    out = []
    for name, envs in RECIPES.items():
        dst = out_dir / f"{name}.wav"
        if not dst.exists():
            parts = [_rms_norm(_channel1(e)) for e in envs]
            n = min(len(p) for p in parts)
            mix = _rms_norm(sum(p[:n] for p in parts))
            write_wav(dst, mix)
            print(f"[noise] wrote {dst.name} ({n / 16000:.0f} s)")
        out.append(dst)
    return out
