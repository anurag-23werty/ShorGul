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
    conds = [c for c in ["phone", "loss_5", "traffic_10", "traffic_5", "market_10", "market_0", "opus_voip", "amrnb_mobile"]
             if c in set(x["condition"])]
    x["model"] = x.A.str.split("/").str[0]
    x["cell"] = [f"{d * 100:+.1f}{'*' if v != 'no significant change' else ''}" for d, v in zip(x["diff"], x.verdict)]
    out = ["| model | lang | " + " | ".join(conds) + " |", "|---" * (len(conds) + 2) + "|"]
    for (model, lang), g in x[~x["lang"].isin(["hinglish_human", "hinglish_heldout", "hi_gv"])].groupby(["model", "lang"]):
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


def findings_table(s: pd.DataFrame, c: pd.DataFrame, results_dir: Path) -> str:
    """The README's headline findings: one row each, number with 95% CI, and the test behind it."""
    import json

    from shorgul.stats.bootstrap import paired
    sc = pd.read_parquet(results_dir / "scored_full.parquet")
    sc = sc[sc["status"].str.startswith("ok")]
    v = json.loads((results_dir / "validation.json").read_text()) if (results_dir / "validation.json").exists() else {}
    h = sc[sc["lang"] == "hinglish"]
    cfg = paired(h[(h.model == "prisma-v2.5") & (h.variant == "matched")], h[(h.model == "prisma-v2.5") & (h.variant == "raw")],
                 "entity_hit_rate")
    rows = []

    def ci_s(pt, lo, hi, d=1, sign=False):
        f = (lambda x: f"{x * 100:+.{d}f}") if sign else (lambda x: f"{x * 100:.{d}f}")
        return f"{f(pt)} [{f(lo)}, {f(hi)}]"

    rows.append(("One API setting decides whether amounts survive (Hinglish, same audio)",
                 f"Prisma v2.5 entity accuracy, `hi-IN` − `en-IN`: **{ci_s(cfg.point, cfg.lo, cfg.hi, sign=True)} pts**",
                 f"paired bootstrap, {cfg.n_clips} clips × all conditions"))
    deg = c[c.comparison.str.endswith("vs clean") & (c.metric == "wer") & c.A.str.startswith("prisma")
            & c.lang.isin(["hi", "bn", "ta", "hinglish"])]
    non0, m0 = deg[deg.condition != "market_0"], deg[deg.condition == "market_0"]
    rows.append(("Phone line, AMR-NB, Opus, packet loss, traffic, 10 dB market",
                 f"no significant WER change in **{(non0.verdict == 'no significant change').sum()} of {len(non0)}** "
                 "Prisma model × language × condition cells", "paired bootstrap vs clean, same clips"))
    rows.append(("0 dB market babble", f"significant WER increase in **{(m0.verdict != 'no significant change').sum()} of {len(m0)}** "
                 f"Prisma cells (+{m0['diff'].min() * 100:.1f} to +{m0['diff'].max() * 100:.1f} pts)", "paired bootstrap vs clean"))
    for lang, name in (("hi", "Hindi"), ("bn", "Bengali"), ("ta", "Tamil")):
        q = c[(c.comparison == "v3.0 vs v2.5") & (c.metric == "wer") & (c.lang == lang) & (c.condition == "ALL")]
        if len(q):
            q = q.iloc[0]
            rows.append((f"Prisma v3.0 vs v2.5, read speech ({name})", f"WER {ci_s(q['diff'], q.lo, q.hi, sign=True)} pts "
                         f"(v3.0 − v2.5)", "paired bootstrap, all conditions"))
    for m, label in (("wer_cn", "currency-neutral WER"), ("entity_hit_rate", "entity accuracy")):
        q = c[(c.comparison == "v3.0 matched vs v2.5 matched") & (c.metric == m) & (c.condition == "ALL")].iloc[0]
        rows.append((f"Prisma v3.0 vs v2.5, Hinglish, same config ({label})", f"{ci_s(q['diff'], q.lo, q.hi, sign=True)} pts: "
                     f"{'tie' if 'tie' in q.verdict else q.verdict}", "paired bootstrap"))
    d = c[c.comparison.str.endswith("denoised vs raw") & (c.condition == "ALL") & (c.metric == "wer")
          & c.A.str.startswith("prisma") & (c.lang != "hinglish")]
    rows.append(("Generic denoiser (spectral gating) before Prisma", f"WER significantly higher in **{d.verdict.str.contains('raw better').sum()} "
                 f"of {len(d)}** Prisma × language cells", "paired bootstrap, noisy conditions pooled"))
    for x in v.get("heldout", []):
        if "en-IN" in x["system"]:
            r = x["held_rep"]
            rows.append(("Entity repair on unseen lines (Prisma v2.5 `en-IN` output)", f"0% → **{ci_s(*r, d=0)}%** entity accuracy",
                         f"held-out: {v['heldout_lines']} lines committed before any audio existed"))
    for rc in v.get("real_calls", []):
        if rc["model"] in ("Prisma v2.5", "Prisma v3.0"):
            a = rc["all"]
            rows.append((f"{rc['model']} on {v['real_calls_n']} real phone calls (Gram Vaani, Hindi)", f"WER {ci_s(*a)}%",
                         "bootstrap over calls"))
    if "real_v30_minus_v25" in v:
        p = v["real_v30_minus_v25"]
        rows.append(("Prisma v3.0 vs v2.5 on the same real calls", f"WER {ci_s(p[0], p[1], p[2], sign=True)} pts", "paired bootstrap"))
    w = s[(s.model == "whisper-small") & (s.variant == "raw") & (s.condition == "clean")].set_index("lang")
    for lang, name in (("hi", "Hindi"), ("ta", "Tamil")):
        if lang in w.index:
            r = w.loc[lang]
            rows.append((f"Whisper-small, clean {name} read speech", f"WER {ci_s(r.wer, r.wer_lo, r.wer_hi)}%", "bootstrap over clips"))
    if "bn" in w.index:
        bn = s[(s.model == "whisper-small") & (s.variant == "raw") & (s.lang == "bn")]
        rows.append(("Whisper-small, Bengali", f"writes Devanagari script in {bn.wrong_script_rate.mean() * 100:.0f}% of transcripts",
                     "script check per transcript"))
    out = ["| finding | number (95% CI) | test |", "|---|---|---|"]
    out += [f"| {a} | {b} | {t} |" for a, b, t in rows]
    return "\n".join(out)


def render(results_dir: Path) -> dict[str, str]:
    s = pd.read_csv(results_dir / "summary.csv")
    c = pd.read_csv(results_dir / "comparisons.csv")
    return {"wer": wer_table(s), "entity": entity_table(s), "claims": claims_table(c),
            "degradation": degradation_table(c), "repair": repair_table(s, c),
            "findings": findings_table(s, c, results_dir)}


def update_readme(readme: Path, tables: dict[str, str]) -> list[str]:
    text, done = readme.read_text(encoding="utf-8"), []
    for name, body in tables.items():
        pat = re.compile(rf"(<!-- table:{name} -->\n).*?(<!-- /table:{name} -->)", re.S)
        if pat.search(text):
            text = pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)
            done.append(name)
    readme.write_text(text, encoding="utf-8")
    return done
