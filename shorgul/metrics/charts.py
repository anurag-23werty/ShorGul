"""README charts (PNG). Fixed categorical colors per series - color follows the model, never rank."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from shorgul.config import load_config  # noqa: E402

SERIES_COLORS = {  # validated reference palette, slots 1-4 (light mode)
    "prisma-v2.5": "#2a78d6", "prisma-v3.0": "#eb6834",
    "whisper-small": "#1baf7a", "prisma-v3.0 + context": "#eda100",
}
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
            s = sub[sub["model"] == model].set_index("condition").reindex(conds)["wer"]
            if s.notna().any():
                ax.plot(range(len(conds)), s.values, color=color, linewidth=2, marker="o",
                        markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.5, label=model)
        ax.set_title(LANG_NAMES[lang], fontsize=10, color=INK, loc="left")
        ax.set_xticks(range(len(conds)), conds, rotation=40, ha="right")
    axes[0][0].set_ylabel("WER (corpus)", color=INK2, fontsize=9)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return out


def _bars(ax, table: pd.DataFrame, conds: list[str]) -> None:
    cols = [c for c in SERIES_COLORS if c in table.columns]
    width = 0.8 / max(len(cols), 1)
    for i, col in enumerate(cols):
        xs = [x + (i - (len(cols) - 1) / 2) * width for x in range(len(conds))]
        ax.bar(xs, table.reindex(conds)[col].values, width=width * 0.9, color=SERIES_COLORS[col], label=col)
    ax.set_xticks(range(len(conds)), conds, rotation=30, ha="right")


def entity_hits(summary: pd.DataFrame, out: Path) -> Path | None:
    h = summary[(summary["lang"] == "hinglish") & summary["entity_hit_rate"].notna()].copy()
    if h.empty:
        return None
    h["series"] = h["model"] + h["variant"].map({"context": " + context"}).fillna("")
    h = h[h["variant"].isin(["raw", "context"])]
    table = h.pivot_table(index="condition", columns="series", values="entity_hit_rate")
    conds = _conditions(h)
    fig, ax = plt.subplots(figsize=(8, 3.6), facecolor=SURFACE)
    _style(ax)
    _bars(ax, table, conds)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Entity hit rate (₹ amounts, dates)", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.15))
    fig.tight_layout()
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return out


def denoise_delta(summary: pd.DataFrame, out: Path) -> Path | None:
    keys = ["lang", "model", "condition"]
    raw = summary[summary["variant"] == "raw"].set_index(keys)["wer"]
    den = summary[summary["variant"] == "denoised"].set_index(keys)["wer"]
    both = (den - raw).dropna()
    if both.empty:
        return None
    # mean over languages, weighting each language equally
    delta = both.groupby(level=["condition", "model"]).mean().unstack("model")
    conds = [c for c in load_config()["conditions"] if c in delta.index]
    fig, ax = plt.subplots(figsize=(7, 3.4), facecolor=SURFACE)
    _style(ax)
    _bars(ax, delta, conds)
    ax.axhline(0, color=INK2, linewidth=1)
    ax.set_ylabel("ΔWER denoised − raw\n(below 0 = denoise helps)", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.15))
    fig.tight_layout()
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return out


def render_charts(summary: pd.DataFrame, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    made = [wer_by_condition(summary, out_dir / "wer_by_condition.png"),
            entity_hits(summary, out_dir / "entity_hit_rate.png"),
            denoise_delta(summary, out_dir / "denoise_delta.png")]
    return [p for p in made if p is not None]
