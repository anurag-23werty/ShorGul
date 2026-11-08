"""`shorgul compare`: a regression gate. Did the candidate model/config get significantly worse?

Both sides are re-scored with the same normalization, matched on (clip_id, condition), and compared
with the paired clip-level bootstrap. Exit 1 only when the candidate is worse by >= --fail-on points
AND the 95% CI excludes zero; a noisy wobble never fails the build.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from shorgul.asr.base import MockASR
from shorgul.config import load_config, path
from shorgul.metrics.aggregate import score_rows
from shorgul.stats.bootstrap import paired

METRIC = {"wer": ("wer_cn", "lower"), "entity": ("entity_hit_rate", "higher")}  # wer = currency-neutral


@dataclass
class Gate:
    table: pd.DataFrame
    regressed: bool
    message: str


def _manifest() -> pd.DataFrame:
    return pd.read_csv(path("manifest"), keep_default_na=False)


def load_side(p: Path, model: str | None, variant: str | None) -> pd.DataFrame:
    df = pd.read_parquet(p) if str(p).endswith(".parquet") else pd.read_csv(p, keep_default_na=False)
    if model and "model" in df:
        df = df[df["model"] == model]
    if variant and "variant" in df:
        df = df[df["variant"] == variant]
    if "entities" not in df:
        df = df.merge(_manifest()[["clip_id", "entities"]], on="clip_id", how="left")
    if "status" not in df:
        df = df.assign(status="ok")
    return df[["clip_id", "lang", "condition", "reference", "hypothesis", "entities", "status"]].fillna("")


def mock_side(model: str, langs: list[str] | None = None) -> pd.DataFrame:
    """Deterministic fake run over every manifest clip x condition (no audio, no API)."""
    m = _manifest()
    if langs:
        m = m[m["lang"].isin(langs)]
    asr, rows = MockASR(model), []
    for r in m.itertuples():
        for cond in load_config()["conditions"]:
            hyp = asr.transcribe(f"{r.clip_id}|{cond}".encode(),
                                 {"_reference": r.reference, "_condition": cond, "_variant": "raw"}).transcript
            rows.append({"clip_id": r.clip_id, "lang": r.lang, "condition": cond, "reference": r.reference,
                         "hypothesis": hyp, "entities": r.entities, "status": "ok"})
    return pd.DataFrame(rows)


def gate(baseline: pd.DataFrame, candidate: pd.DataFrame, metric: str, fail_on: float) -> Gate:
    col, better = METRIC[metric]
    a, b = score_rows(candidate), score_rows(baseline)
    keys = ["clip_id", "condition"]
    common = a[keys].merge(b[keys], on=keys)
    a, b = a.merge(common, on=keys), b.merge(common, on=keys)
    if metric == "entity":
        a, b = a[a["entities"] != ""], b[b["entities"] != ""]
    if a.empty:
        raise ValueError("no overlapping (clip_id, condition) rows to compare")
    rows = []
    for lang in sorted(a["lang"].unique()):
        for cond in [*load_config()["conditions"], "ALL"]:
            aa = a[(a["lang"] == lang) & ((a["condition"] == cond) if cond != "ALL" else True)]
            bb = b[(b["lang"] == lang) & ((b["condition"] == cond) if cond != "ALL" else True)]
            if aa.empty:
                continue
            r = paired(aa, bb, col)
            worse_by = (r.point if better == "lower" else -r.point) * 100
            sig_worse = (r.lo > 0) if better == "lower" else (r.hi < 0)
            sig_better = (r.hi < 0) if better == "lower" else (r.lo > 0)
            verdict = ("REGRESSION" if sig_worse and worse_by >= fail_on else
                       "worse (below threshold)" if sig_worse else "improved" if sig_better else "no significant change")
            rows.append({"lang": lang, "condition": cond, "metric": col, "candidate_minus_baseline_pts": round(r.point * 100, 2),
                         "ci_lo": round(r.lo * 100, 2), "ci_hi": round(r.hi * 100, 2), "n_clips": r.n_clips,
                         "verdict": verdict})
    t = pd.DataFrame(rows)
    bad = t[t["verdict"] == "REGRESSION"]
    msg = (f"FAIL: {len(bad)} significant regression(s) of >= {fail_on} pts {metric}" if len(bad)
           else f"PASS: no significant {metric} regression of >= {fail_on} pts")
    return Gate(t, bool(len(bad)), msg)
