"""README hero GIF: the finding on one real clip (cached transcripts), numbers from results/.

Needs libraqm for correct Devanagari shaping (macOS: brew install libraqm; run with
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib). Refuses to render without it rather than ship broken text.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont, features

from shorgul.config import path
from shorgul.entities.repair import repair

W, H = 1100, 440
BG, INK, INK2, LINE = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
GOOD, BAD, ACCENT = "#008300", "#e34948", "#2a78d6"
FONT_CANDIDATES = ["/System/Library/Fonts/Kohinoor.ttc", "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"]
ENT = re.compile(r"^(₹?\d[\d,]*|मार्च|march|5)$", re.I)
WRONG = {"chaar", "hazaar", "paanch", "sau", "rupay", "march"}


def _font(size: int, bold: bool = False):
    if not features.check("raqm"):
        raise RuntimeError("libraqm not available: Devanagari would render incorrectly (see module docstring)")
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size, index=2 if bold and p.endswith(".ttc") else 0,
                                      layout_engine=ImageFont.Layout.RAQM)
    raise RuntimeError("no Devanagari font found")


def _words(d: ImageDraw.ImageDraw, x: int, y: int, text: str, font, colors: dict[str, str], maxw: int) -> int:
    """Draw text word by word, wrapping, colouring words found in `colors`. Returns the next y."""
    sp = font.getlength(" ")
    cx = x
    lh = int(font.size * 1.55)
    for w in text.split():
        wl = font.getlength(w)
        if cx + wl > x + maxw:
            cx, y = x, y + lh
        key = w.strip("।,.").lower()
        col = colors.get(key, INK)
        if col != INK:
            d.rounded_rectangle([cx - 4, y - 2, cx + wl + 4, y + font.size + 10], radius=6,
                                fill="#e7f3e7" if col == GOOD else "#fbe4e4")
        d.text((cx, y), w, font=font, fill=col)
        cx += wl + sp
    return y + lh


def _frame(title: str, sub: str, text: str | None, colors: dict, badge: tuple[str, str] | None, foot: str) -> Image.Image:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((48, 36), title, font=_font(34, bold=True), fill=INK)
    d.text((48, 86), sub, font=_font(21), fill=INK2)
    d.line([(48, 128), (W - 48, 128)], fill=LINE, width=2)
    y = 156
    if text:
        y = _words(d, 48, y, text, _font(30), colors, W - 96)
    if badge:
        label, col = badge
        f = _font(24, bold=True)
        bw = f.getlength(label) + 36
        d.rounded_rectangle([48, y + 10, 48 + bw, y + 54], radius=22, fill=col)
        d.text((66, y + 16), label, font=f, fill="white")
    _words(d, 48, H - 92, foot, _font(20), {}, W - 96)
    d.text((W - 210, H - 36), "ShorGul Bench", font=_font(16), fill=INK2)
    return im


def _num(s: pd.DataFrame, model: str, variant: str, cond: str, m: str) -> str:
    r = s[(s.lang == "hinglish") & (s.model == model) & (s.variant == variant) & (s.condition == cond)].iloc[0]
    return f"{r[m]:.0%} [{r[m + '_lo']:.0%}, {r[m + '_hi']:.0%}]"


def build(out: Path) -> Path:
    rdir = path("results")
    h = pd.read_parquet(rdir / "hyps.parquet")
    s = pd.read_csv(rdir / "summary.csv")
    c = pd.read_csv(rdir / "comparisons.csv")
    x = h[(h.clip_id == "hg_000") & (h.condition == "clean")].set_index(["model", "variant"])["hypothesis"]
    ref = h[h.clip_id == "hg_000"].iloc[0]["reference"]
    en, hi, v3 = x[("prisma-v2.5", "raw")], x[("prisma-v2.5", "matched")], x[("prisma-v3.0", "raw")]
    good = {"₹4,500": GOOD, "4,500": GOOD, "5": GOOD, "मार्च": GOOD, "march": GOOD}
    bad = {w: BAD for w in WRONG}
    cw = c[(c.comparison == "v3.0 matched vs v2.5 matched") & (c.condition == "ALL")].set_index("metric")
    rp = c[(c.comparison == "repaired vs raw") & (c.lang == "hinglish") & (c.condition == "ALL")
           & (c.metric == "entity_hit_rate") & (c.A == "prisma-v2.5/raw+repair")].iloc[0]
    frames = [
        _frame("Same call. Same model. One setting.", "Hinglish customer-care line · clean audio · what the caller said:",
               ref, good, None, "Watch the ₹ amount and the date."),
        _frame("Prisma v2.5 · language_code = en-IN", "transcript", en, bad, ("amount missed · date missed", BAD),
               f"Benchmark, 25 clips: entity accuracy {_num(s, 'prisma-v2.5', 'raw', 'clean', 'entity_hit_rate')}. "
               "Romanized number words; English formatting can't convert them."),
        _frame("Prisma v2.5 · language_code = hi-IN", "same model, same audio, one parameter changed", hi, good,
               ("amount found · date found", GOOD),
               f"Benchmark: entity accuracy {_num(s, 'prisma-v2.5', 'matched', 'clean', 'entity_hit_rate')}."),
        _frame("Prisma v3.0", "writes 4,500 रुपये, where the reference writes ₹4,500", v3, good, ("amount found · date found", GOOD),
               f"WER as scored: v2.5 better by {cw.loc['wer', 'diff'] * 100:.1f} pts (significant). Drop the ₹/रुपये "
               f"convention: {cw.loc['wer_cn', 'diff'] * 100:+.1f} [{cw.loc['wer_cn', 'lo'] * 100:+.1f}, "
               f"{cw.loc['wer_cn', 'hi'] * 100:+.1f}], a tie. The metric picked the winner."),
        _frame("The fix: ShorGul entity repair", "applied to the en-IN transcript, no new API call", repair(en), good,
               ("amount found · date found", GOOD),
               f"Entity accuracy {rp['diff'] * 100:+.0f} pts [{rp['lo'] * 100:+.0f}, {rp['hi'] * 100:+.0f}] "
               "on en-IN output · 0 regressions on all 3,825 transcripts."),
        _frame("WER misleads Indian voice-AI teams.", "ShorGul tests the config, the call and the entities.", None, {},
               None, "bench · audit your own audio · regression gate in CI"),
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=[3200, 3600, 3600, 5200, 4200, 3000],
                   loop=0, optimize=True)
    return out
