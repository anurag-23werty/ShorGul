"""Label-free stability: how much does a model's transcript change when the audio degrades?

stability(clip, condition) = CER(transcript_of_original, transcript_of_degraded)

0 = identical output; higher = the call conditions are changing what the model hears. Needs no
reference transcript, so it works on a customer's own audio.
"""
from __future__ import annotations

import jiwer
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from shorgul.metrics.wer_cer import prep


def stability(clean_hyp: str, degraded_hyp: str, lang: str) -> float:
    a, b = prep(clean_hyp, lang), prep(degraded_hyp, lang)
    if not a and not b:
        return 0.0
    if not a or not b:
        return 1.0
    return float(min(jiwer.cer(a, b), 1.5))  # cap runaway loops so one clip can't dominate


def stability_table(scored: pd.DataFrame, variant: str = "raw") -> pd.DataFrame:
    """One row per (lang, model, clip, degraded condition): stability + true WER increase."""
    ok = scored[(scored["variant"] == variant) & scored["status"].str.startswith("ok")]
    clean = ok[ok["condition"] == "clean"].set_index(["lang", "model", "clip_id"])
    rows = []
    for r in ok[ok["condition"] != "clean"].itertuples():
        key = (r.lang, r.model, r.clip_id)
        if key not in clean.index:
            continue
        c = clean.loc[key]
        rows.append({"lang": r.lang, "model": r.model, "clip_id": r.clip_id, "condition": r.condition,
                     "stability": stability(c["hypothesis"], r.hypothesis, r.lang),
                     "wer_increase": r.wer - c["wer"]})
    return pd.DataFrame(rows)


def validate(table: pd.DataFrame) -> pd.DataFrame:
    """Spearman ρ between stability and true WER increase, pooled and per model."""
    out = []
    groups = [("all models", table)] + [(m, g) for m, g in table.groupby("model")]
    for name, g in groups:
        rho, p = spearmanr(g["stability"], g["wer_increase"])
        out.append({"model": name, "n": len(g), "spearman_rho": round(float(rho), 3), "p_value": float(p)})
    return pd.DataFrame(out)


def calibrate(table: pd.DataFrame) -> pd.DataFrame:
    """Mean true WER increase per stability band. This is what the audit grade means in WER terms."""
    bands = [0, 0.05, 0.10, 0.20, 0.35, np.inf]
    labels = ["A (<5%)", "B (5-10%)", "C (10-20%)", "D (20-35%)", "F (>=35%)"]
    t = table.assign(band=pd.cut(table["stability"], bands, labels=labels, right=False))
    return (t.groupby("band", observed=False)["wer_increase"]
            .agg(n="size", mean_wer_increase="mean", median_wer_increase="median").reset_index())


# Folder-level grade bands on mean stability (validated ≈ expected WER increase, see validation chart)
GRADES = [(0.02, "A"), (0.05, "B"), (0.10, "C"), (0.20, "D"), (float("inf"), "F")]


def grade(mean_stability: float) -> str:
    return next(g for cut, g in GRADES if mean_stability < cut)


def folder_level(table: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    """Mean stability per (lang, model, condition) next to the true corpus-WER increase."""
    s = summary[(summary["variant"] == "raw")]
    clean = s[s["condition"] == "clean"].set_index(["lang", "model"])["wer"]
    s = s[s["condition"] != "clean"].copy()
    s["wer_increase"] = [w - clean.get((l, m), np.nan) for l, m, w in zip(s["lang"], s["model"], s["wer"])]
    g = table.groupby(["lang", "model", "condition"])["stability"].mean().rename("mean_stability").reset_index()
    return g.merge(s[["lang", "model", "condition", "wer_increase"]], on=["lang", "model", "condition"])


def plot_validation(table: pd.DataFrame, folder: pd.DataFrame, out) -> tuple[float, float]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shorgul.metrics.charts import INK, INK2, SERIES_COLORS, SURFACE, _style

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor=SURFACE)
    for ax in axes:
        _style(ax)
        ax.grid(axis="x", color="#e6e5e0", linewidth=0.8)
    pr = table[table["model"].str.startswith("prisma")]
    for m, g in pr.groupby("model"):
        axes[0].scatter(g["stability"], g["wer_increase"], s=10, alpha=0.45, color=SERIES_COLORS[m], label=m,
                        linewidths=0)
    rho_c, p_c = spearmanr(pr["stability"], pr["wer_increase"])
    axes[0].set_title(f"Per clip (Prisma, FLEURS): Spearman ρ = {rho_c:.2f}, p = {p_c:.1g}",
                      fontsize=9, color=INK, loc="left")
    axes[0].set_xlabel("stability = CER(original transcript, degraded transcript)", fontsize=8, color=INK2)
    axes[0].set_ylabel("true WER increase vs clean", fontsize=8, color=INK2)
    axes[0].legend(frameon=False, fontsize=8)
    fp = folder[folder["model"].str.startswith("prisma")]
    for m, g in folder.groupby("model"):
        axes[1].scatter(g["mean_stability"], g["wer_increase"], s=36, color=SERIES_COLORS[m], label=m,
                        edgecolor=SURFACE, linewidth=1)
    lim = max(folder["mean_stability"].max(), folder["wer_increase"].max()) * 1.05
    axes[1].plot([0, lim], [0, lim], color=INK2, linewidth=1, linestyle="--")
    axes[1].text(lim * 0.62, lim * 0.55, "y = x", fontsize=8, color=INK2)
    rho_f, p_f = spearmanr(fp["mean_stability"], fp["wer_increase"])
    axes[1].set_title(f"Per folder (lang × model × condition): Prisma ρ = {rho_f:.2f}, p = {p_f:.1g}",
                      fontsize=9, color=INK, loc="left")
    axes[1].set_xlabel("mean stability (no reference needed)", fontsize=8, color=INK2)
    axes[1].set_ylabel("true corpus-WER increase vs clean", fontsize=8, color=INK2)
    axes[1].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return float(rho_c), float(p_c)
