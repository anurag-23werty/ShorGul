"""README banner: assets/banner.svg (self-contained, text as vector outlines) + assets/banner.png (1600x560).

The waveform is REAL: clip hg_000 as recorded, through the simulated phone line, and with 0 dB market noise
(the benchmark's own degraded files). The chip shows that clip's real amount and date as Prisma v3.0 wrote them.
Fonts: Geist / Geist Mono (SIL OFL, assets/fonts). Run:  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  .venv/bin/python scripts/make_banner.py
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from shorgul.audio import read_wav  # noqa: E402

W, H, PAD = 1600, 560, 80
BG, INK, INK2, INK3, LINE, ACCENT = "#0B0B0C", "#EDEDED", "#A1A1A6", "#6E6E73", "#232326", "#FF6A1A"
FONTS = ROOT / "assets" / "fonts"
CLIP = "hg_000"
STAGES = [("clean", "clean call"), ("phone", "phone line · 8 kHz μ-law"), ("market_0", "market noise · 0 dB")]


@lru_cache(maxsize=None)
def font(name: str, weight: int) -> TTFont:
    return instantiateVariableFont(TTFont(FONTS / name), {"wght": weight}, inplace=False)


def text_path(s: str, x: float, y: float, size: float, name="Geist-VF.ttf", weight=400,
              tracking: float = 0.0) -> tuple[str, float]:
    """SVG path data for `s` with baseline at (x, y); returns (d, advance_width)."""
    f = font(name, weight)
    gs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
    scale = size / f["head"].unitsPerEm
    pen, cx = SVGPathPen(gs), x
    for ch in s:
        g = cmap.get(ord(ch), cmap.get(ord("?")))
        gs[g].draw(TransformPen(pen, (scale, 0, 0, -scale, cx, y)))
        cx += hmtx[g][0] * scale + tracking * size
    return pen.getCommands(), cx - x


def bars(peaks: np.ndarray, x0: float, x1: float, mid: float, half: float, color: str, gap=1.6) -> str:
    n = len(peaks)
    step = (x1 - x0) / n
    w = max(step - gap, 1.0)
    out = []
    for i, p in enumerate(peaks):
        h = max(1.5, float(p) * half)
        out.append(f'<rect x="{x0 + i * step:.1f}" y="{mid - h:.1f}" width="{w:.1f}" height="{2 * h:.1f}" rx="{min(w / 2, 1.2):.1f}"/>')
    return f'<g fill="{color}">{"".join(out)}</g>'


def peaks_of(x: np.ndarray, n: int) -> np.ndarray:
    k = len(x) // n
    p = np.abs(x[: k * n]).reshape(n, k).max(axis=1)
    return p


def build() -> str:
    waves = {s: read_wav(ROOT / "data" / "degraded" / s / f"{CLIP}.wav") for s, _ in STAGES}
    ref = max(float(np.abs(w).max()) for w in waves.values())
    parts = [f'<rect width="{W}" height="{H}" fill="{BG}"/>']
    d, _ = text_path("ShorGul", PAD, 196, 128, weight=600, tracking=-0.035)
    parts.append(f'<path d="{d}" fill="{INK}"/>')
    d, _ = text_path("Testing Indian-language speech AI on real phone conditions", PAD + 4, 252, 32, weight=400,
                     tracking=-0.01)
    parts.append(f'<path d="{d}" fill="{INK2}"/>')

    # the chip: the money survives
    chip_txt = "₹4,500 · 5 March"
    d_chip, cw = text_path(chip_txt, 0, 0, 26, name="GeistMono-VF.ttf", weight=500)
    cx1 = W - PAD
    cx0 = cx1 - cw - 44
    cy, ch = 382 - 28, 56
    d_chip, _ = text_path(chip_txt, cx0 + 22, cy + 37, 26, name="GeistMono-VF.ttf", weight=500)
    parts.append(f'<rect x="{cx0:.1f}" y="{cy}" width="{cx1 - cx0:.1f}" height="{ch}" rx="10" fill="none" '
                 f'stroke="{ACCENT}" stroke-width="1.6"/>')
    parts.append(f'<path d="{d_chip}" fill="{ACCENT}"/>')
    d, _ = text_path("amount · date, as transcribed", cx0, 300, 17, name="GeistMono-VF.ttf")
    parts.append(f'<path d="{d}" fill="{INK3}"/>')
    d, _ = text_path(f"clip {CLIP} · real benchmark audio", cx0, cy + ch + 34, 15, name="GeistMono-VF.ttf")
    parts.append(f'<path d="{d}" fill="{INK3}"/>')

    # the story strip: same real call, three real stages, left to right
    sx0, sx1, mid, half = PAD, cx0 - 64, 382, 62
    seg_w, gap = (sx1 - sx0 - 2 * 44) / 3, 44
    for i, (stage, label) in enumerate(STAGES):
        x0 = sx0 + i * (seg_w + gap)
        p = peaks_of(waves[stage], 120) / ref
        parts.append(bars(p, x0, x0 + seg_w, mid, half, INK if stage != "market_0" else INK2))
        d, _ = text_path(label, x0, 300, 17, name="GeistMono-VF.ttf", weight=400)
        parts.append(f'<path d="{d}" fill="{INK3}"/>')
        if i < 3:
            ax = x0 + seg_w + gap / 2 if i < 2 else sx1 + 32
            d, _ = text_path("→", ax - 9, mid + 7, 20, name="GeistMono-VF.ttf")
            parts.append(f'<path d="{d}" fill="{INK3}"/>')
    parts.append(f'<line x1="{sx0}" x2="{sx1}" y1="{mid + half + 26}" y2="{mid + half + 26}" stroke="{LINE}" stroke-width="1"/>')

    d, _ = text_path("Built on Gnani Prisma v2.5 · v3.0 · Timbre", PAD, H - 56, 18, name="GeistMono-VF.ttf")
    parts.append(f'<path d="{d}" fill="{INK3}"/>')
    title = "ShorGul: testing Indian-language speech AI on real phone conditions"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'role="img" aria-label="{title}"><title>{title}</title>{"".join(parts)}</svg>')


def main() -> None:
    import cairosvg
    out = ROOT / "assets"
    svg = build()
    (out / "banner.svg").write_text(svg, encoding="utf-8")
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out / "banner.png"), output_width=W, output_height=H)
    print(f"[banner] assets/banner.svg ({len(svg) / 1024:.0f} KB), assets/banner.png "
          f"({(out / 'banner.png').stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
