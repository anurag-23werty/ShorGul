"""Audio health check: estimate SNR, bandwidth and clipping, then map a clip to the nearest
benchmark condition, so the benchmark tells a customer what to expect from their own audio."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from shorgul.audio import SR, read_wav

FRAME = SR * 20 // 1000


@dataclass
class Health:
    snr_db: float          # energy-VAD estimate: loud-frame vs quiet-frame power
    hf_ratio: float        # share of spectral energy above 4.2 kHz: ≈0 once audio has passed an 8 kHz phone line
    clipping_pct: float    # % samples at |x| >= 0.99
    speech_pct: float      # % frames classed as speech
    dropout_pct: float     # % of 20 ms frames that are digital silence *inside* the speech span (packet loss)
    duration_s: float

    def as_dict(self) -> dict:
        return {k: round(v, 3) for k, v in asdict(self).items()}


def _short_runs(mask: np.ndarray, max_len: int) -> np.ndarray:
    """Keep only True-runs of length <= max_len (dropped packets), drop long digital silences."""
    out = np.zeros_like(mask)
    i, n = 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i <= max_len:
                out[i:j] = True
            i = j
        else:
            i += 1
    return out


def check(audio: np.ndarray) -> Health:
    n = len(audio) // FRAME
    if n < 5:
        return Health(float("nan"), float("nan"), 0.0, 0.0, 0.0, len(audio) / SR)
    frames = audio[: n * FRAME].reshape(n, FRAME)
    p = np.mean(frames**2, axis=1) + 1e-12
    db = 10 * np.log10(p)
    noise_db, speech_db = np.percentile(db, 10), np.percentile(db, 90)
    speech = db > noise_db + 0.5 * (speech_db - noise_db)
    spec = np.abs(np.fft.rfft(audio * np.hanning(len(audio)))) ** 2
    freqs = np.fft.rfftfreq(len(audio), 1 / SR)
    hf = float(spec[freqs > 4200].sum() / (spec[freqs > 80].sum() + 1e-12))
    zero = np.abs(frames).max(axis=1) < 1e-4
    nz = np.flatnonzero(~zero)
    inner = zero[nz[0]: nz[-1] + 1] if len(nz) else zero
    inner = _short_runs(inner, max_len=3)  # packet-sized gaps (20-60 ms) only, not VAD-gated silences
    return Health(snr_db=float(speech_db - noise_db), hf_ratio=hf,
                  clipping_pct=float(100 * np.mean(np.abs(audio) >= 0.99)),
                  speech_pct=float(100 * speech.mean()), dropout_pct=float(100 * inner.mean()),
                  duration_s=len(audio) / SR)


def check_file(p: str | Path) -> Health:
    return check(read_wav(p))


def condition_profiles(degraded_dir: Path, conditions: list[str], max_clips: int = 40) -> pd.DataFrame:
    """Median health features of each benchmark condition, from the degraded benchmark audio."""
    rows = []
    for cond in conditions:
        files = sorted((degraded_dir / cond).glob("*.wav"))[:max_clips]
        for f in files:
            rows.append({"condition": cond, **check_file(f).as_dict()})
    if not rows:
        return pd.DataFrame(columns=["condition", "snr_db", "hf_ratio"])
    return pd.DataFrame(rows).groupby("condition")[["snr_db", "hf_ratio"]].median().reset_index()


WIDEBAND_HF = 3e-4      # energy share above 4.2 kHz; benchmark clean median 3.4e-3, every phone clip <= 2e-4
DROPOUT_PCT = 1.5       # loss_5 median 5.1%, every other condition 0%


def nearest_condition(h: Health, profiles: pd.DataFrame) -> str:
    """Transparent rules, calibrated on the benchmark audio:
    packet-sized dropouts -> loss_5; wideband -> clean; otherwise nearest phone/noise condition by SNR."""
    if np.isnan(h.snr_db):
        return "unknown"
    if h.dropout_pct >= DROPOUT_PCT:  # most specific signal first: wideband VoIP drops packets too
        return "loss_5"
    if h.hf_ratio >= WIDEBAND_HF:
        return "clean"
    cands = profiles[~profiles["condition"].isin(["clean", "loss_5"])]
    if cands.empty:
        return "phone"
    return str(cands.loc[(cands["snr_db"] - h.snr_db).abs().idxmin(), "condition"])
