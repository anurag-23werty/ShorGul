"""Generate README tables (with 95% CIs) from summary.csv / comparisons.csv, between markers:
<!-- table:NAME --> ... <!-- /table:NAME -->. Numbers are never hand-typed."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

LANGS = [("hi", "Hindi"), ("bn", "Bengali"), ("ta", "Tamil"), ("hinglish", "Hinglish*")]


def _pct(v: float) -> str:
    return "–" if pd.isna(v) else f"{v * 100:.1f}%"


def _ci(r: pd.Series, m: str) -> str:
    return f"{_pct(r[m])} [{r[m + '_lo'] * 100:.1f}, {r[m + '_hi'] * 100:.1f}]"


def _row(s: pd.DataFrame, lang: str, model: str, variant: str, cond: str) -> pd.Series | None:
    x = s[(s.lang == lang) & (s.model == model) & (s.variant == variant) & (s.condition == cond)]
    return None if x.empty else x.iloc[0]


def wer_table(s: pd.DataFrame) -> str:
    rows = [("Prisma v2.5", "prisma-v2.5", "raw"), ("Prisma v3.0", "prisma-v3.0", "raw"),
            ("Prisma v3.0 + context", "prisma-v3.0", "context"), ("Whisper-small", "whisper-small", "raw")]
    out = ["| | " + " | ".join(n for _, n in LANGS) + " |", "|---" * (len(LANGS) + 1) + "|"]
    for label, model, var in rows:
        cells = []
        for lang, _ in LANGS:
            c, w = _row(s, lang, model, var, "clean"), _row(s, lang, model, var, "market_0")
            cells.append("–" if c is None else f"{_ci(c, 'wer')} → {_ci(w, 'wer')}")
        out.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def entity_table(s: pd.DataFrame) -> str:
    rows = [("Prisma v3.0 (`hi-IN,en-IN`)", "prisma-v3.0", "raw"), ("Prisma v2.5 (`hi-IN`, matched)", "prisma-v2.5", "matched"),
            ("Prisma v3.0 (`hi-IN`, matched)", "prisma-v3.0", "matched"), ("Prisma v3.0 + context", "prisma-v3.0", "context"),
            ("Whisper-small", "whisper-small", "raw"), ("Prisma v2.5 (`en-IN`)", "prisma-v2.5", "raw")]
    out = ["| | clean | market_0 |", "|---|---|---|"]
    for label, model, var in rows:
        c, w = _row(s, "hinglish", model, var, "clean"), _row(s, "hinglish", model, var, "market_0")
        if c is not None:
            out.append(f"| {label} | {_ci(c, 'entity_hit_rate')} | {_ci(w, 'entity_hit_rate')} |")
    return "\n".join(out)


def claims_table(c: pd.DataFrame) -> str:
    """Every model-vs-model claim in the README, pooled over conditions unless stated."""
    want = [("v3.0 vs v2.5", m, l, "ALL") for l in ("hi", "bn", "ta") for m in ("wer",)]
    want += [("v3.0 vs v2.5", "wer", l, "clean") for l in ("hi", "bn", "ta")]
    want += [("v3.0 matched vs v2.5 matched", m, "hinglish", "ALL") for m in ("wer", "wer_cn", "entity_hit_rate")]
    want += [("v3.0 context vs v3.0 raw", m, "hinglish", "ALL") for m in ("wer", "entity_hit_rate")]
    want += [(f"{m} denoised vs raw", "wer", l, "ALL") for m in ("prisma-v2.5", "prisma-v3.0", "whisper-small")
             for l in ("hi", "bn", "ta", "hinglish")]
    names = {"wer": "WER", "wer_cn": "WER (currency-neutral)", "entity_hit_rate": "entity acc.", "cer": "CER"}
    out = ["| claim (A − B) | lang | conditions | metric | Δ (pts) | 95% CI | verdict |", "|---|---|---|---|---|---|---|"]
    for comp, metric, lang, cond in want:
        x = c[(c.comparison == comp) & (c.metric == metric) & (c.lang == lang) & (c.condition == cond)]
        if x.empty:
            continue
        r = x.iloc[0]
        out.append(f"| {comp} | {lang} | {'all' if cond == 'ALL' else cond} | {names[metric]} | "
                   f"{r['diff'] * 100:+.1f} | [{r.lo * 100:+.1f}, {r.hi * 100:+.1f}] | {r.verdict} |")
    return "\n".join(out)


def degradation_table(c: pd.DataFrame) -> str:
    x = c[c.comparison.str.endswith("vs clean") & (c.metric == "wer") & c.A.str.startswith("prisma")].copy()
    conds = ["phone", "loss_5", "traffic_10", "traffic_5", "market_10", "market_0"]
    x["model"] = x.A.str.split("/").str[0]
    x["cell"] = [f"{d * 100:+.1f}{'*' if v != 'no significant change' else ''}" for d, v in zip(x["diff"], x.verdict)]
    out = ["| model | lang | " + " | ".join(conds) + " |", "|---" * (len(conds) + 2) + "|"]
    for (model, lang), g in x.groupby(["model", "lang"]):
        g = g.set_index("condition")
        out.append(f"| {model} | {lang} | " + " | ".join(g.loc[k, "cell"] if k in g.index else "–" for k in conds) + " |")
    return "\n".join(out)


def repair_table(s: pd.DataFrame, c: pd.DataFrame) -> str:
    """Hinglish: entity accuracy and WER, raw vs entity-repaired, pooled over all 7 conditions (paired)."""
    rows = [("Prisma v2.5 (`en-IN`)", "prisma-v2.5", "raw"), ("Prisma v2.5 (`hi-IN`)", "prisma-v2.5", "matched"),
            ("Prisma v3.0", "prisma-v3.0", "raw"), ("Prisma v3.0 + context", "prisma-v3.0", "context"),
            ("Whisper-small", "whisper-small", "raw")]
    out = ["| model (Hinglish) | entity acc. raw → repaired | Δ entity [95% CI] | Δ WER as scored | "
           "Δ WER currency-neutral |", "|---|---|---|---|---|"]
    for label, model, var in rows:
        g = s[(s.lang == "hinglish") & (s.model == model) & (s.variant == var)]
        if g.empty:
            continue
        cc = c[(c.comparison == "repaired vs raw") & (c.lang == "hinglish") & (c.condition == "ALL")
               & (c.A == f"{model}/{var}+repair")]

        def cell(metric: str) -> str:
            r = cc[cc.metric == metric]
            if r.empty:
                return "–"
            r = r.iloc[0]
            star = "" if r.verdict == "no significant change" else " *"
            return f"{r['diff'] * 100:+.1f} [{r.lo * 100:+.1f}, {r.hi * 100:+.1f}]{star}"

        out.append(f"| {label} | {g.entity_hit_rate.mean() * 100:.0f}% → {g.entity_rep.mean() * 100:.0f}% | "
                   f"{cell('entity_hit_rate')} | {cell('wer')} | {cell('wer_cn')} |")
    return "\n".join(out)


def render(results_dir: Path) -> dict[str, str]:
    s = pd.read_csv(results_dir / "summary.csv")
    c = pd.read_csv(results_dir / "comparisons.csv")
    return {"wer": wer_table(s), "entity": entity_table(s), "claims": claims_table(c),
            "degradation": degradation_table(c), "repair": repair_table(s, c)}


def update_readme(readme: Path, tables: dict[str, str]) -> list[str]:
    text, done = readme.read_text(encoding="utf-8"), []
    for name, body in tables.items():
        pat = re.compile(rf"(<!-- table:{name} -->\n).*?(<!-- /table:{name} -->)", re.S)
        if pat.search(text):
            text = pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)
            done.append(name)
    readme.write_text(text, encoding="utf-8")
    return done
