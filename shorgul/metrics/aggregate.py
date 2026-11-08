"""Score hypotheses -> results.parquet (per row), summary.csv (per group, with 95% CIs)
and comparisons.csv (paired-bootstrap model-vs-model and fix-vs-raw tests)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from shorgul.config import load_config
from shorgul.metrics.entities import entity_hit_rate
from shorgul.metrics.wer_cer import error_counts, prep
from shorgul.stats.bootstrap import ci, paired

RESULT_COLS = ["clip_id", "lang", "source", "condition", "variant", "model", "reference",
               "hypothesis", "wer", "cer", "entity_hit_rate", "latency_s", "status"]
GROUP = ["lang", "model", "variant", "condition"]
SCRIPT_RANGES = {"hi": ("ऀ", "ॿ"), "bn": ("ঀ", "৿"), "ta": ("஀", "௿")}
CI_METRICS = ["wer", "wer_cn", "cer", "entity_hit_rate"]


def wrong_script(hypothesis: str, lang: str) -> bool:
    """True if most letters of the hypothesis are outside the language's own script (e.g. Bengali in Devanagari)."""
    if lang not in SCRIPT_RANGES:
        return False
    letters = [c for c in hypothesis if c.isalpha() or "ऀ" <= c <= "෿"]
    if not letters:
        return False
    lo, hi = SCRIPT_RANGES[lang]
    return sum(lo <= c <= hi for c in letters) / len(letters) < 0.5


def score_rows(hyps: pd.DataFrame) -> pd.DataFrame:
    out = hyps.copy()
    ok = out["status"].str.startswith("ok").to_numpy()
    counts = np.array([error_counts(r, h, l) for r, h, l in zip(out["reference"], out["hypothesis"], out["lang"])])
    cn = np.array([error_counts(r, h, l, currency_neutral=(l == "hinglish"))
                   for r, h, l in zip(out["reference"], out["hypothesis"], out["lang"])])
    out["word_err"], out["ref_words"], out["char_err"], out["ref_chars"] = counts.T
    out["word_err_cn"], out["ref_words_cn"] = cn[:, 0], cn[:, 1]
    for col in ["word_err", "char_err", "word_err_cn"]:  # failed calls carry no errors -> excluded
        out[col] = out[col].astype(float).where(ok)
    out["wer"] = out["word_err"] / out["ref_words"].clip(lower=1)
    out["wer_cn"] = out["word_err_cn"] / out["ref_words_cn"].clip(lower=1)
    out["cer"] = out["char_err"] / out["ref_chars"].clip(lower=1)
    out["entity_hit_rate"] = [entity_hit_rate(e, h) if good else np.nan
                              for e, h, good in zip(out["entities"], out["hypothesis"], ok)]
    hyp_norm = [prep(h, l) for h, l in zip(out["hypothesis"], out["lang"])]
    # hallucination / repetition loops: hypothesis >2x longer than the reference (words or chars)
    out["runaway"] = ((np.array([len(h.split()) for h in hyp_norm]) > 2 * out["ref_words"])
                      | (np.array([len(h) for h in hyp_norm]) > 2 * out["ref_chars"]))
    out["wrong_script"] = [wrong_script(h, l) for h, l in zip(out["hypothesis"], out["lang"])]
    return out


def summarize(scored: pd.DataFrame) -> pd.DataFrame:
    ok = scored[scored["status"].str.startswith("ok")]
    rows = []
    for key, g in ok.groupby(GROUP):
        row = dict(zip(GROUP, key), n=len(g))
        for m in CI_METRICS:
            row[m], row[f"{m}_lo"], row[f"{m}_hi"] = ci(g, m)
        row.update(median_wer=g["wer"].median(), runaway_rate=g["runaway"].mean(),
                   wrong_script_rate=g["wrong_script"].mean(), latency_s=g["latency_s"].median())
        rows.append(row)
    summ = pd.DataFrame(rows)
    errs = scored.groupby(GROUP)["status"].apply(lambda s: int((~s.str.startswith("ok")).sum()))
    summ = summ.merge(errs.rename("n_errors").reset_index(), on=GROUP, how="left")
    summ["n_errors"] = summ["n_errors"].fillna(0).astype(int)
    return summ.round(4)


def _pairs(langs: list[str]) -> list[tuple[str, str, str, str, str, list[str]]]:
    """(label, model_a, variant_a, model_b, variant_b, langs) for every claim the README makes."""
    noisy = load_config()["noisy_conditions"]
    p = [("v3.0 vs v2.5", "prisma-v3.0", "raw", "prisma-v2.5", "raw", langs),
         ("v3.0 vs whisper", "prisma-v3.0", "raw", "whisper-small", "raw", langs),
         ("v2.5 vs whisper", "prisma-v2.5", "raw", "whisper-small", "raw", langs),
         ("v3.0 matched vs v2.5 matched", "prisma-v3.0", "matched", "prisma-v2.5", "matched", ["hinglish"]),
         ("v3.0 context vs v3.0 raw", "prisma-v3.0", "context", "prisma-v3.0", "raw", ["hinglish"])]
    for m in ["prisma-v2.5", "prisma-v3.0", "whisper-small"]:
        p.append((f"{m} denoised vs raw", m, "denoised", m, "raw", langs))
    return [(*x, noisy if "denoised" in x[0] else None) for x in p]


def compare(scored: pd.DataFrame) -> pd.DataFrame:
    """Paired bootstrap for every claim: per condition and pooled over conditions. Diff = A - B."""
    ok = scored[scored["status"].str.startswith("ok")]
    langs = sorted(ok["lang"].unique())
    conds_all = list(load_config()["conditions"])
    out = []
    for label, ma, va, mb, vb, lang_set, only_conds in _pairs(langs):
        for lang in lang_set:
            a = ok[(ok["lang"] == lang) & (ok["model"] == ma) & (ok["variant"] == va)]
            b = ok[(ok["lang"] == lang) & (ok["model"] == mb) & (ok["variant"] == vb)]
            if a.empty or b.empty:
                continue
            conds = only_conds or conds_all
            metrics = ["wer", "cer"] + (["wer_cn", "entity_hit_rate"] if lang == "hinglish" else [])
            for scope in conds + ["ALL"]:
                cs = conds if scope == "ALL" else [scope]
                aa, bb = a[a["condition"].isin(cs)], b[b["condition"].isin(cs)]
                for m in metrics:
                    r = paired(aa, bb, m)
                    if r.n_clips == 0:
                        continue
                    better = "lower" if m != "entity_hit_rate" else "higher"
                    if not r.significant:
                        verdict = "tie (not significant)"
                    else:
                        a_wins = (r.point < 0) == (better == "lower")
                        verdict = f"{f'{ma}/{va}' if a_wins else f'{mb}/{vb}'} better (significant)"
                    out.append(dict(comparison=label, A=f"{ma}/{va}", B=f"{mb}/{vb}", lang=lang,
                                    condition=scope, metric=m, diff=r.point, lo=r.lo, hi=r.hi, p=r.p,
                                    n_clips=r.n_clips, verdict=verdict))
    out += _degradation_vs_clean(ok)
    return pd.DataFrame(out).round(4)


def _degradation_vs_clean(ok: pd.DataFrame) -> list[dict]:
    """Same model, same clips: condition X minus clean. Answers 'does the phone line hurt?'"""
    out = []
    for (lang, model), g in ok[ok["variant"] == "raw"].groupby(["lang", "model"]):
        clean = g[g["condition"] == "clean"].assign(condition="x")
        metrics = ["wer"] + (["wer_cn", "entity_hit_rate"] if lang == "hinglish" else [])
        for cond in [c for c in load_config()["conditions"] if c != "clean"]:
            deg = g[g["condition"] == cond].assign(condition="x")
            for m in metrics:
                r = paired(deg, clean, m)
                if r.n_clips == 0:
                    continue
                worse = (r.point > 0) if m != "entity_hit_rate" else (r.point < 0)
                verdict = ("no significant change" if not r.significant
                           else f"significantly {'worse' if worse else 'better'} than clean")
                out.append(dict(comparison=f"{cond} vs clean", A=f"{model}/raw@{cond}", B=f"{model}/raw@clean",
                                lang=lang, condition=cond, metric=m, diff=r.point, lo=r.lo, hi=r.hi, p=r.p,
                                n_clips=r.n_clips, verdict=verdict))
    return out
