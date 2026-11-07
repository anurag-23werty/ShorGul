"""Condition = noise (caller side, acoustic) -> phone channel -> packet loss. Writes wavs + log."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from shorgul.audio import read_wav, write_wav
from shorgul.config import ROOT, load_config, path, seed_for
from shorgul.degrade.noise import mix_at_snr
from shorgul.degrade.packet_loss import apply_packet_loss
from shorgul.degrade.telephony import phone_channel


def degrade_audio(audio: np.ndarray, clip_id: str, condition: str,
                  noises: dict[str, np.ndarray]) -> tuple[np.ndarray, dict]:
    cfg = load_config()
    spec = cfg["conditions"][condition] or {}
    rng = np.random.default_rng(seed_for(clip_id, condition))
    info: dict = {"snr_target": spec.get("snr_db"), "loss_frac": 0.0}
    out = audio
    if "noise" in spec:
        out = mix_at_snr(out, noises[spec["noise"]], spec["snr_db"], rng)
    if spec.get("phone"):
        ph = cfg["phone"]
        out = phone_channel(out, ph["low_hz"], ph["high_hz"], ph["codec_rate"])
    if spec.get("loss"):
        out, info["loss_frac"] = apply_packet_loss(out, spec["loss"], rng, cfg["packet_loss"]["frame_ms"])
    return out.astype(np.float32), info


def degraded_path(condition: str, clip_id: str) -> Path:
    return path("degraded") / condition / f"{clip_id}.wav"


def load_noises() -> dict[str, np.ndarray]:
    return {p.stem: read_wav(p) for p in path("noise").glob("*.wav")}


def degrade_all(manifest: pd.DataFrame, conditions: list[str], force: bool = False) -> pd.DataFrame:
    noises = load_noises()
    logs = []
    for row in manifest.itertuples():
        clean = read_wav(ROOT / row.audio_path)
        for cond in conditions:
            dst = degraded_path(cond, row.clip_id)
            if dst.exists() and not force:
                continue
            out, info = degrade_audio(clean, row.clip_id, cond, noises)
            write_wav(dst, out)
            rms = float(np.sqrt(np.mean(out**2)))
            logs.append({"clip_id": row.clip_id, "condition": cond,
                         "rms_db": round(20 * np.log10(rms + 1e-12), 2), **info})
    log = pd.DataFrame(logs)
    if len(log):
        lp = path("degraded") / "degrade_log.csv"
        if lp.exists():
            old = pd.read_csv(lp)
            log = pd.concat([old.merge(log[["clip_id", "condition"]], how="left", indicator=True)
                             .query("_merge=='left_only'").drop(columns="_merge"), log], ignore_index=True)
        log.to_csv(lp, index=False)
    return log
