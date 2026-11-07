"""Score hypotheses -> results.parquet (per row) and summary.csv (per group, corpus-level)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from shorgul.metrics.entities import entity_hit_rate
from shorgul.metrics.wer_cer import prep, wer_cer

RESULT_COLS = ["clip_id", "lang", "source", "condition", "variant", "model", "reference",
               "hypothesis", "wer", "cer", "entity_hit_rate", "latency_s", "status"]
GROUP = ["lang", "model", "variant", "condition"]
SCRIPT_RANGES = {"hi": ("\u0900", "\u097f"), "bn": ("\u0980", "\u09ff"), "ta": ("\u0b80", "\u0bff")}


def wrong_script(hypothesis: str, lang: str) -> bool:
    """True if most letters of the hypothesis are outside the language's own script (e.g. Bengali in Devanagari)."""
    if lang not in SCRIPT_RANGES:
        return False
    letters = [c for c in hypothesis if c.isalpha() or "\u0900" <= c <= "\u0dff"]
    if not letters:
        return False
    lo, hi = SCRIPT_RANGES[lang]
    return sum(lo <= c <= hi for c in letters) / len(letters) < 0.5


def score_rows(hyps: pd.DataFrame) -> pd.DataFrame:
    out = hyps.copy()
    ok = out["status"].str.startswith("ok")
    metrics = [wer_cer(r, h, l) if good else (np.nan, np.nan)
               for r, h, l, good in zip(out["reference"], out["hypothesis"], out["lang"], ok)]
    out["wer"] = [m[0] for m in metrics]
    out["cer"] = [m[1] for m in metrics]
    out["entity_hit_rate"] = [entity_hit_rate(e, h) if good else np.nan
                              for e, h, good in zip(out["entities"], out["hypothesis"], ok)]
    out["ref_words"] = [len(prep(r, l).split()) for r, l in zip(out["reference"], out["lang"])]
    out["ref_chars"] = [len(prep(r, l)) for r, l in zip(out["reference"], out["lang"])]
    hyp_norm = [prep(h, l) for h, l in zip(out["hypothesis"], out["lang"])]
    # hallucination / repetition loops: hypothesis >2x longer than the reference (words or chars)
    out["runaway"] = ((np.array([len(h.split()) for h in hyp_norm]) > 2 * out["ref_words"])
                      | (np.array([len(h) for h in hyp_norm]) > 2 * out["ref_chars"]))
    out["wrong_script"] = [wrong_script(h, l) for h, l in zip(out["hypothesis"], out["lang"])]
    return out


def summarize(scored: pd.DataFrame) -> pd.DataFrame:
    ok = scored[scored["status"].str.startswith("ok")]

    def agg(g: pd.DataFrame) -> pd.Series:
        return pd.Series({
            "n": int(len(g)),
            "wer": (g["wer"] * g["ref_words"]).sum() / max(g["ref_words"].sum(), 1),  # corpus WER
            "cer": (g["cer"] * g["ref_chars"]).sum() / max(g["ref_chars"].sum(), 1),
            "median_wer": g["wer"].median(),
            "entity_hit_rate": g["entity_hit_rate"].mean(),
            "runaway_rate": g["runaway"].mean(),
            "wrong_script_rate": g["wrong_script"].mean(),
            "latency_s": g["latency_s"].median(),
        })

    summ = ok.groupby(GROUP).apply(agg, include_groups=False).reset_index()
    errs = scored.groupby(GROUP)["status"].apply(lambda s: (~s.str.startswith("ok")).sum())
    summ = summ.merge(errs.rename("n_errors").reset_index(), on=GROUP, how="left")
    summ["n"] = summ["n"].astype(int)
    summ["n_errors"] = summ["n_errors"].fillna(0).astype(int)
    return summ.round(4)
