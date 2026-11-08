"""README charts (PNG). Fixed categorical colors per series - color follows the model, never rank."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from shorgul.config import load_config  # noqa: E402

SERIES_COLORS = {  # validated reference palette, slots 1-4 (light mode); fixed per series, never by rank
    "prisma-v2.5": "#2a78d6", "prisma-v3.0": "#eb6834",
    "whisper-small": "#1baf7a", "prisma-v3.0 + context": "#eda100",
}
# Hinglish entity chart names the language_code, because it decides the result (results/finding_check.md)
ENTITY_SERIES = {("prisma-v2.5", "raw"): "prisma-v2.5 (en-IN)", ("prisma-v2.5", "matched"): "prisma-v2.5 (hi-IN)",
                 ("prisma-v3.0", "raw"): "prisma-v3.0", ("prisma-v3.0", "context"): "prisma-v3.0 + context",
                 ("whisper-small", "raw"): "whisper-small"}
ENTITY_COLORS = {"prisma-v2.5 (en-IN)": "#a9c8ef", "prisma-v2.5 (hi-IN)": "#2a78d6", "prisma-v3.0": "#eb6834",
                 "prisma-v3.0 + context": "#eda100", "whisper-small": "#1baf7a"}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
LANG_NAMES = {"hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "hinglish": "Hinglish (call-centre)"}


def _style(ax) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8, length=0)


def _conditions(summary: pd.DataFrame) -> list[str]:
    return [c for c in load_config()["conditions"] if c in set(summary["condition"])]


def wer_by_condition(summary: pd.DataFrame, out: Path) -> Path | None:
    raw = summary[summary["variant"] == "raw"]
    if raw.empty:
        return None
    langs = [l for l in LANG_NAMES if l in set(raw["lang"])]
    conds = _conditions(raw)
    fig, axes = plt.subplots(1, len(langs), figsize=(3.6 * len(langs), 3.4), sharey=True,
                             squeeze=False, facecolor=SURFACE)
    for ax, lang in zip(axes[0], langs):
        _style(ax)
        sub = raw[raw["lang"] == lang]
        for model, color in SERIES_COLORS.items():
            g = sub[sub["model"] == model].set_index("condition").reindex(conds)
            if g["wer"].notna().any():
                x = range(len(conds))
                if "wer_lo" in g:
                    ax.fill_between(x, g["wer_lo"], g["wer_hi"], color=color, alpha=0.15, linewidth=0)
                ax.plot(x, g["wer"].values, color=color, linewidth=2, marker="o",
                        markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.5, label=model)
        ax.set_title(LANG_NAMES[lang], fontsize=10, color=INK, loc="left")
        ax.set_xticks(range(len(conds)), conds, rotation=40, ha="right")
    axes[0][0].set_ylabel("WER (corpus), band = 95% CI", color=INK2, fontsize=9)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return out


def _bars(ax, table: pd.DataFrame, conds: list[str], lo: pd.DataFrame | None = None,
          hi: pd.DataFrame | None = None, colors: dict[str, str] | None = None) -> None:
    colors = colors or SERIES_COLORS
    cols = [c for c in colors if c in table.columns]
    width = 0.8 / max(len(cols), 1)
    for i, col in enumerate(cols):
        xs = [x + (i - (len(cols) - 1) / 2) * width for x in range(len(conds))]
        vals = table.reindex(conds)[col].values
        yerr = None
        if lo is not None and hi is not None:
            l, h = lo.reindex(conds)[col].values, hi.reindex(conds)[col].values
            yerr = [vals - l, h - vals]
        ax.bar(xs, vals, width=width * 0.9, color=colors[col], label=col,
               yerr=yerr, error_kw={"ecolor": INK2, "elinewidth": 1, "capsize": 2})
        for x, v in zip(xs, vals):
            if v == 0:  # a zero bar is invisible: say it, so 0 isn't read as "not run"
                ax.text(x, 0.01, "0", ha="center", va="bottom", fontsize=7, color=INK2)
    ax.set_xticks(range(len(conds)), conds, rotation=30, ha="right")


def entity_hits(summary: pd.DataFrame, out: Path) -> Path | None:
    h = summary[(summary["lang"] == "hinglish") & summary["entity_hit_rate"].notna()].copy()
    if h.empty:
        return None
    h["series"] = [ENTITY_SERIES.get((m, v)) for m, v in zip(h["model"], h["variant"])]
    h = h[h["series"].notna()]
    piv = {k: h.pivot_table(index="condition", columns="series", values=v)
           for k, v in (("p", "entity_hit_rate"), ("lo", "entity_hit_rate_lo"), ("hi", "entity_hit_rate_hi"))
           if v in h}
    conds = _conditions(h)
    fig, ax = plt.subplots(figsize=(9, 3.8), facecolor=SURFACE)
    _style(ax)
    _bars(ax, piv["p"], conds, piv.get("lo"), piv.get("hi"), ENTITY_COLORS)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Entity hit rate (₹ amounts, dates)\nwhiskers = 95% CI", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.17))
    fig.tight_layout()
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return out


def denoise_delta(comparisons: pd.DataFrame | None, out: Path) -> Path | None:
    """Paired-bootstrap ΔWER (denoised − raw), pooled over the noisy conditions, per language."""
    if comparisons is None or comparisons.empty:
        return None
    c = comparisons[comparisons["comparison"].str.endswith("denoised vs raw") & (comparisons["condition"] == "ALL")
                    & (comparisons["metric"] == "wer")].copy()
    if c.empty:
        return None
    c["model"] = c["A"].str.split("/").str[0]
    langs = [l for l in LANG_NAMES if l in set(c["lang"])]
    piv = {k: c.pivot_table(index="lang", columns="model", values=k) for k in ("diff", "lo", "hi")}
    fig, ax = plt.subplots(figsize=(7.5, 3.6), facecolor=SURFACE)
    _style(ax)
    _bars(ax, piv["diff"], langs, piv["lo"], piv["hi"])
    ax.set_xticks(range(len(langs)), [LANG_NAMES[l].split(" (")[0] for l in langs], rotation=0, ha="center")
    ax.axhline(0, color=INK2, linewidth=1)
    ax.set_ylabel("ΔWER denoised − raw (paired, 95% CI)\nabove 0 = denoise hurts", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.15))
    fig.tight_layout()
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return out


def render_charts(summary: pd.DataFrame, out_dir: Path, comparisons: pd.DataFrame | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    made = [wer_by_condition(summary, out_dir / "wer_by_condition.png"),
            entity_hits(summary, out_dir / "entity_hit_rate.png"),
            denoise_delta(comparisons, out_dir / "denoise_delta.png")]
    return [p for p in made if p is not None]
