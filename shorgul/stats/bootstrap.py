"""Clip-level bootstrap CIs and paired (cluster) bootstrap tests.

Corpus WER/CER are ratios of sums (errors / reference units), so each resample recomputes the
ratio from resampled per-clip error counts, never by averaging per-clip WERs.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

B = 1000
SEED = 20261110
ALPHA = 0.05

# metric -> (numerator column, denominator column or None for a plain mean)
METRICS: dict[str, tuple[str, str | None]] = {
    "wer": ("word_err", "ref_words"),
    "wer_cn": ("word_err_cn", "ref_words_cn"),  # currency-convention-neutral (Hinglish)
    "cer": ("char_err", "ref_chars"),
    "entity_hit_rate": ("entity_hit_rate", None),
}


def _stat(num: np.ndarray, den: np.ndarray | None) -> np.ndarray:
    """num/den: (..., n) arrays -> statistic over the last axis."""
    if den is None:
        return np.nanmean(num, axis=-1)
    return num.sum(axis=-1) / np.maximum(den.sum(axis=-1), 1)


def ci(df: pd.DataFrame, metric: str, b: int = B, seed: int = SEED) -> tuple[float, float, float]:
    """Point estimate + percentile 95% CI, resampling rows (one row per clip within a group)."""
    ncol, dcol = METRICS[metric]
    num = df[ncol].to_numpy(float)
    den = df[dcol].to_numpy(float) if dcol else None
    if dcol is None:
        keep = ~np.isnan(num)
        num = num[keep]
    if len(num) == 0:
        return (np.nan, np.nan, np.nan)
    point = float(_stat(num, den))
    idx = np.random.default_rng(seed).integers(0, len(num), size=(b, len(num)))
    boots = _stat(num[idx], den[idx] if den is not None else None)
    lo, hi = np.nanpercentile(boots, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return point, float(lo), float(hi)


@dataclass
class Paired:
    point: float      # stat(A) - stat(B)
    lo: float
    hi: float
    p: float          # two-sided bootstrap p-value
    n_clips: int

    @property
    def significant(self) -> bool:
        return self.lo > 0 or self.hi < 0


def paired(a: pd.DataFrame, b_: pd.DataFrame, metric: str, b: int = B, seed: int = SEED) -> Paired:
    """A minus B on the same (clip, condition) units; resamples whole clips (cluster bootstrap),
    so pooling several conditions keeps each clip's conditions together."""
    ncol, dcol = METRICS[metric]
    keys = ["clip_id", "condition"]
    cols = [ncol] + ([dcol] if dcol else [])
    m = a[keys + cols].merge(b_[keys + cols], on=keys, suffixes=("_a", "_b"))
    if dcol is None:
        m = m.dropna(subset=[f"{ncol}_a", f"{ncol}_b"])
    if m.empty:
        return Paired(np.nan, np.nan, np.nan, np.nan, 0)
    clips = m["clip_id"].unique()
    # per-clip sums -> (n_clips,) arrays; plain means are sums of values / count of units
    g = m.groupby("clip_id")
    if dcol is None:
        na, nb = g[f"{ncol}_a"].sum().to_numpy(), g[f"{ncol}_b"].sum().to_numpy()
        da = db = g.size().to_numpy().astype(float)
    else:
        na, nb = g[f"{ncol}_a"].sum().to_numpy(), g[f"{ncol}_b"].sum().to_numpy()
        da, db = g[f"{dcol}_a"].sum().to_numpy(), g[f"{dcol}_b"].sum().to_numpy()

    def diff(ix):
        return (na[ix].sum(-1) / np.maximum(da[ix].sum(-1), 1)) - (nb[ix].sum(-1) / np.maximum(db[ix].sum(-1), 1))

    point = float(diff(np.arange(len(clips))))
    idx = np.random.default_rng(seed).integers(0, len(clips), size=(b, len(clips)))
    boots = diff(idx)
    lo, hi = np.percentile(boots, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    p = float(min(1.0, 2 * min((boots <= 0).mean(), (boots >= 0).mean())))
    return Paired(point, float(lo), float(hi), p, len(clips))
