"""Render an AuditResult as one self-contained report.html (inline CSS, base64 charts and audio)."""
from __future__ import annotations

import base64
import io
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402

from shorgul.audit.run import BREAK_AT, GRADE_TEXT, AuditResult  # noqa: E402
from shorgul.metrics.charts import INK, INK2, SURFACE, _style  # noqa: E402

TEMPLATES = Path(__file__).parent / "templates"
GRADE_COLOR = {"A": "#008300", "B": "#1baf7a", "C": "#eda100", "D": "#eb6834", "F": "#e34948"}


def _png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _wav(p: Path) -> str | None:
    return "data:audio/wav;base64," + base64.b64encode(p.read_bytes()).decode() if p.exists() else None


def stability_chart(res: AuditResult) -> str:
    pc = res.summary["per_condition"]
    fig, ax = plt.subplots(figsize=(6.5, 2.8), facecolor=SURFACE)
    _style(ax)
    xs = range(len(pc))
    colors = [GRADE_COLOR[g] for g in pc["grade"]]
    ax.bar(xs, pc["stability"], color=colors, width=0.55,
           yerr=[pc["stability"] - pc["lo"], pc["hi"] - pc["stability"]],
           error_kw={"ecolor": INK2, "elinewidth": 1, "capsize": 3})
    ax.axhline(BREAK_AT, color=INK2, linewidth=1, linestyle="--")
    ax.text(len(pc) - 0.5, BREAK_AT, " breaking point", va="bottom", ha="right", fontsize=7, color=INK2)
    for x, (s, g) in enumerate(zip(pc["stability"], pc["grade"])):
        ax.text(x, s, f"{s:.1%}  {g}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(list(xs), pc["condition"], fontsize=8)
    ax.set_ylabel("stability (transcript change)\nwhiskers = 95% CI", fontsize=8, color=INK2)
    return _png(fig)


def render(res: AuditResult, out_dir: Path) -> Path:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
    worst = []
    for w in res.summary["worst"]:
        worst.append({**w, "audio_original": _wav(out_dir / "original" / f"{w['clip_id']}.wav"),
                      "audio_degraded": _wav(out_dir / w["condition"] / f"{w['clip_id']}.wav")})
    html = env.get_template("report.html.j2").render(
        r=res, s=res.summary, grade_text=GRADE_TEXT[res.summary["grade"]], grade_color=GRADE_COLOR,
        chart=stability_chart(res), worst=worst, clips=res.clips.to_dict("records"), today=date.today().isoformat(),
        break_at=BREAK_AT)
    out = out_dir / "report.html"
    out.write_text(html, encoding="utf-8")
    return out
