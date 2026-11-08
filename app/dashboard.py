"""ShorGul dashboard: streamlit run app/dashboard.py"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shorgul.config import load_config, path  # noqa: E402
from shorgul.entities.lexicon import MONTHS  # noqa: E402
from shorgul.entities.repair import repair  # noqa: E402
from shorgul.metrics.charts import ENTITY_COLORS, ENTITY_SERIES, LANG_NAMES, SERIES_COLORS  # noqa: E402
from shorgul.stats.bootstrap import ci  # noqa: E402

st.set_page_config(page_title="ShorGul", layout="wide")
CONDS = list(load_config()["conditions"])
COLOR = alt.Scale(domain=list(SERIES_COLORS), range=list(SERIES_COLORS.values()))
ECOLOR = alt.Scale(domain=list(ENTITY_COLORS), range=list(ENTITY_COLORS.values()))
INK2 = "#52514e"


# ---------------------------------------------------------------- data
@st.cache_data
def load(mock: bool):
    rdir = path("results") / ("mock" if mock else "")
    scored = pd.read_parquet(rdir / "scored_full.parquet")
    summary = pd.read_csv(rdir / "summary.csv")
    comp = pd.read_csv(rdir / "comparisons.csv") if (rdir / "comparisons.csv").exists() else pd.DataFrame()
    for df in (scored, summary):
        df["series"] = df["model"] + df["variant"].map({"context": " + context"}).fillna("")
        df["eseries"] = [ENTITY_SERIES.get((m, v)) for m, v in zip(df["model"], df["variant"])]
    return scored, summary, comp


@st.cache_data
def pooled(scored: pd.DataFrame, lang: str, metric: str, key: str = "eseries") -> pd.DataFrame:
    """Point + 95% CI pooled over all conditions (clip-level bootstrap), per series."""
    ok = scored[(scored["lang"] == lang) & scored["status"].str.startswith("ok") & scored[key].notna()]
    rows = []
    for s, g in ok.groupby(key):
        p, lo, hi = ci(g, metric)
        rows.append({"series": s, "value": p, "lo": lo, "hi": hi})
    return pd.DataFrame(rows)


def comp_row(comp: pd.DataFrame, **kw) -> pd.Series | None:
    x = comp
    for k, v in kw.items():
        x = x[x[k] == v]
    return None if x.empty else x.iloc[0]


MONTH_WORDS = sorted({w for ws in MONTHS.values() for w in ws if len(w) > 3}, key=len, reverse=True)
ENT_RE = re.compile(r"(₹?\d[\d,]*(?:\.\d+)?|" + "|".join(map(re.escape, MONTH_WORDS)) + r")", re.I)


def mark(text: str) -> str:
    """HTML-escape and highlight amounts/dates."""
    return ENT_RE.sub(lambda m: f"<mark>{m.group(0)}</mark>", html.escape(text or ""))


def pct(v: float) -> str:
    return "–" if pd.isna(v) else f"{v:.1%}"


# ---------------------------------------------------------------- header
st.title("ShorGul")
st.markdown("#### WER misleads Indian voice-AI teams, and here's the fix.")
st.caption("Telephony robustness + entity-accuracy testing for Indian-language ASR. "
           "Built on Gnani Prisma v2.5, v3.0 and Timbre. All brackets are 95% bootstrap CIs over clips.")

real_ok = (path("results") / "summary.csv").exists()
mock_ok = (path("results") / "mock" / "summary.csv").exists()
if not (real_ok or mock_ok):
    st.error("No results yet. Run `python -m shorgul.cli score` (or `score --mock`).")
    st.stop()
with st.sidebar:
    source = st.radio("Data", [s for s, ok in (("real", real_ok), ("mock", mock_ok)) if ok])
    st.caption("mock = synthetic transcripts for testing the pipeline; not model output.")
scored, summary, comp = load(source == "mock")
_need = {"entity_hit_rate_rep", "wer_cn", "hyp_repaired"}
if not _need <= set(scored.columns):
    st.error(f"These results were scored by an older version. Re-run `python -m shorgul.cli score"
             f"{' --mock' if source == 'mock' else ''}` (missing: {', '.join(sorted(_need - set(scored.columns)))}).")
    st.stop()
if source == "mock":
    st.warning("MOCK data: synthetic transcripts, not real model output.")

tabs = st.tabs(["1 · The finding", "2 · The fix", "3 · Degradation", "4 · Listen & compare",
                "5 · Try your audio", "6 · Sample audit", "7 · Method & limits"])

# ---------------------------------------------------------------- 1. finding
with tabs[0]:
    st.subheader("Your eval config picks the winner, not the model")
    st.markdown(
        "On **identical** Hinglish call-centre audio, one request parameter (`language_code`) moved Prisma v2.5's "
        "entity accuracy from **0% to ~94%**. And one reference-writing convention (`₹4,500` vs `4,500 रुपये`) "
        "decides which model \"wins\" on WER. With default settings, WER alone can pick the wrong model.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Same audio, three configs: entity accuracy** (pooled over 7 conditions)")
        e = pooled(scored, "hinglish", "entity_hit_rate")
        e = e[e["series"].isin(["prisma-v2.5 (en-IN)", "prisma-v2.5 (hi-IN)", "prisma-v3.0"])]
        if len(e):
            base = alt.Chart(e).encode(y=alt.Y("series:N", title=None, sort=list(ENTITY_COLORS)))
            st.altair_chart(
                (base.mark_bar(cornerRadiusEnd=3).encode(
                    x=alt.X("value:Q", title="entity accuracy (₹ amounts, dates)", axis=alt.Axis(format="%"),
                            scale=alt.Scale(domain=[0, 1])),
                    color=alt.Color("series:N", scale=ECOLOR, legend=None),
                    tooltip=["series", alt.Tooltip("value:Q", format=".1%"), alt.Tooltip("lo:Q", format=".1%"),
                             alt.Tooltip("hi:Q", format=".1%")])
                 + base.mark_rule(color=INK2).encode(x="lo:Q", x2="hi:Q")
                 + base.mark_text(align="left", dx=6, color=INK2).encode(
                     x="hi:Q", text=alt.Text("value:Q", format=".0%"))).properties(height=170),
                width="stretch")
        st.caption("Same model (v2.5), same audio: `en-IN` returns romanized number words that its English "
                   "number formatting can't convert; `hi-IN` returns ₹4,500.")
    with c2:
        st.markdown("**Matched config (both `hi-IN`): v3.0 − v2.5, paired**")
        rows = []
        for metric, label in [("wer", "WER as scored"), ("wer_cn", "WER, currency-neutral"),
                              ("entity_hit_rate", "entity accuracy")]:
            r = comp_row(comp, comparison="v3.0 matched vs v2.5 matched", lang="hinglish", condition="ALL",
                         metric=metric) if len(comp) else None
            if r is not None:
                rows.append({"metric": label, "diff": r["diff"], "lo": r["lo"], "hi": r["hi"], "verdict": r["verdict"]})
        if rows:
            d = pd.DataFrame(rows)
            base = alt.Chart(d).encode(y=alt.Y("metric:N", title=None, sort=[r["metric"] for r in rows]))
            st.altair_chart(
                (alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=INK2, strokeDash=[4, 3]).encode(x="x:Q")
                 + base.mark_rule(strokeWidth=3, color="#eb6834").encode(
                     x=alt.X("lo:Q", title="v3.0 − v2.5 (points); whisker = 95% CI", axis=alt.Axis(format="%")),
                     x2="hi:Q")
                 + base.mark_point(filled=True, size=90, color="#eb6834").encode(
                     x="diff:Q", tooltip=["metric", alt.Tooltip("diff:Q", format="+.1%"),
                                          alt.Tooltip("lo:Q", format="+.1%"), alt.Tooltip("hi:Q", format="+.1%"),
                                          "verdict"])).properties(height=170), width="stretch")
            st.caption("As scored, v2.5 \"wins\" WER significantly. Neutralize ₹ vs रुपये and the gap is inside "
                       "the noise; entity accuracy is a tie too.")
    st.markdown("**Side by side: what you'd conclude from each metric**")
    rk = []
    s_h = summary[(summary["lang"] == "hinglish")]
    for (m, v), label in [(("prisma-v2.5", "raw"), "Prisma v2.5 (en-IN, default-style)"),
                          (("prisma-v2.5", "matched"), "Prisma v2.5 (hi-IN)"), (("prisma-v3.0", "raw"), "Prisma v3.0"),
                          (("whisper-small", "raw"), "Whisper-small")]:
        g = scored[(scored["lang"] == "hinglish") & (scored["model"] == m) & (scored["variant"] == v)
                   & scored["status"].str.startswith("ok")]
        if g.empty:
            continue
        w, wl, wh = ci(g, "wer")
        n, nl, nh = ci(g, "wer_cn")
        en, el, eh = ci(g, "entity_hit_rate")
        rk.append({"system": label, "WER as scored": f"{w:.1%} [{wl:.1%}, {wh:.1%}]",
                   "WER currency-neutral": f"{n:.1%} [{nl:.1%}, {nh:.1%}]",
                   "entity accuracy": f"{en:.0%} [{el:.0%}, {eh:.0%}]", "_w": w, "_e": en})
    if rk:
        t = pd.DataFrame(rk)
        t["WER rank"] = t["_w"].rank().astype(int)
        t["entity rank"] = (-t["_e"]).rank(method="min").astype(int)
        st.dataframe(t.drop(columns=["_w", "_e"]), hide_index=True, width="stretch")
    st.caption("Full write-up: results/finding_check.md. Hinglish clips are TTS (Gnani Timbre), 25 lines.")

# ---------------------------------------------------------------- 2. fix
with tabs[1]:
    st.subheader("The fix: entity repair, a model-agnostic post-processor")
    st.markdown("`shorgul.entities.repair` turns spoken amounts and dates into written form (*chaar hazaar paanch "
                "sau rupay → ₹4,500*, *1 8 अगस्त → 18 अगस्त*, *3/1/May → 31 May*). It only converts in an entity "
                "context, so *do teen log* and *kar do* stay untouched. **0 regressions on all transcripts.**")
    before = pooled(scored, "hinglish", "entity_hit_rate").rename(columns={"value": "raw", "lo": "raw_lo", "hi": "raw_hi"})
    after = pooled(scored, "hinglish", "entity_rep").rename(columns={"value": "repaired", "lo": "rep_lo", "hi": "rep_hi"})
    if len(before):
        dd = before.merge(after, on="series")
        long = pd.concat([dd.assign(stage="raw", v=dd["raw"]), dd.assign(stage="repaired", v=dd["repaired"])])
        base = alt.Chart(long).encode(y=alt.Y("series:N", title=None, sort=list(ENTITY_COLORS)))
        st.altair_chart(
            (alt.Chart(dd).mark_rule(color="#d9d8d3", strokeWidth=4).encode(
                y=alt.Y("series:N", sort=list(ENTITY_COLORS)), x="raw:Q", x2="repaired:Q")
             + base.mark_point(size=110, filled=True).encode(
                 x=alt.X("v:Q", title="Hinglish entity accuracy (pooled; ○ raw  ● repaired)", axis=alt.Axis(format="%"),
                         scale=alt.Scale(domain=[0, 1.02])),
                 color=alt.Color("series:N", scale=ECOLOR, legend=None),
                 shape=alt.Shape("stage:N", scale=alt.Scale(domain=["raw", "repaired"], range=["circle", "circle"]),
                                 legend=None),
                 opacity=alt.Opacity("stage:N", scale=alt.Scale(domain=["raw", "repaired"], range=[0.35, 1]),
                                     legend=None),
                 tooltip=["series", "stage", alt.Tooltip("v:Q", format=".1%")])).properties(height=230),
            width="stretch")
    rows = []
    for (m, v), label in ENTITY_SERIES.items():
        r = comp_row(comp, comparison="repaired vs raw", lang="hinglish", condition="ALL", metric="entity_hit_rate",
                     A=f"{m}/{v}+repair") if len(comp) else None
        rc = comp_row(comp, comparison="repaired vs raw", lang="hinglish", condition="ALL", metric="wer_cn",
                      A=f"{m}/{v}+repair") if len(comp) else None
        if r is not None:
            rows.append({"model": label, "Δ entity (pts)": f"{r['diff']*100:+.1f} [{r['lo']*100:+.1f}, {r['hi']*100:+.1f}]",
                         "Δ WER currency-neutral (pts)": "–" if rc is None else
                         f"{rc['diff']*100:+.1f} [{rc['lo']*100:+.1f}, {rc['hi']*100:+.1f}]",
                         "verdict": r["verdict"]})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.info("Honest positioning: on Prisma output with `format=transcribe`, Gnani's own formatting already writes "
            "amounts correctly. Repair's gains there are small and not significant on 25 clips. Repair is the fix for "
            "verbatim/romanized output and other vendors' models, and for the split-date bugs that formatting leaves. "
            "It can't recover a misheard number (18 अगस्त → 1 August).")
    st.markdown("**Per condition** (entity accuracy, raw → repaired)")
    h = summary[(summary["lang"] == "hinglish") & summary["eseries"].notna()]
    if len(h):
        p = h.assign(cell=[f"{a:.0%} → {b:.0%}" for a, b in zip(h["entity_hit_rate"], h["entity_rep"])]) \
            .pivot_table(index="eseries", columns="condition", values="cell", aggfunc="first")
        st.dataframe(p[[c for c in CONDS if c in p.columns]], width="stretch")

# ---------------------------------------------------------------- 3. degradation
with tabs[2]:
    st.subheader("How WER degrades on simulated Indian phone calls")
    c1, c2, c3 = st.columns([2, 2, 1])
    langs = c1.multiselect("Language", sorted(summary["lang"].unique()), default=sorted(summary["lang"].unique()),
                           format_func=lambda l: LANG_NAMES.get(l, l))
    series = c2.multiselect("Model", list(SERIES_COLORS),
                            default=[s for s in ["prisma-v2.5", "prisma-v3.0", "whisper-small"] if s in set(summary["series"])])
    variant = c3.radio("Audio", ["raw", "denoised"], help="denoised = spectral gating on the received audio")
    metric = st.radio("Metric", ["wer", "cer"], horizontal=True, format_func=str.upper)
    view = summary[summary["lang"].isin(langs) & summary["series"].isin(series)
                   & ((summary["variant"] == variant) | (summary["variant"] == "context"))]
    if len(view):
        base = alt.Chart(view).encode(x=alt.X("condition:N", sort=CONDS, title=None),
                                      color=alt.Color("series:N", scale=COLOR, title="Model"))
        band = base.mark_area(opacity=0.15).encode(y=alt.Y(f"{metric}_lo:Q"), y2=f"{metric}_hi:Q")
        line = base.mark_line(point=alt.OverlayMarkDef(size=55, filled=True), strokeWidth=2).encode(
            y=alt.Y(f"{metric}:Q", title=f"{metric.upper()} (band = 95% CI)", axis=alt.Axis(format="%")),
            tooltip=["lang", "series", "condition", alt.Tooltip(f"{metric}:Q", format=".1%"),
                     alt.Tooltip(f"{metric}_lo:Q", format=".1%", title="CI low"),
                     alt.Tooltip(f"{metric}_hi:Q", format=".1%", title="CI high"), "n",
                     alt.Tooltip("runaway_rate:Q", format=".0%", title="runaway")])
        st.altair_chart((band + line).properties(height=240, width=240).facet(
            column=alt.Column("lang:N", title=None, sort=list(LANG_NAMES))))
    st.caption("Conditions: noise is mixed at the caller (acoustic SNR), then 300–3400 Hz band, 8 kHz μ-law, "
               "and packet loss. Hinglish WER uses the original (en-IN) v2.5 config; see tab 1.")
    if len(comp):
        st.markdown("**Does the condition hurt? Paired change vs clean (same model, same clips)**")
        x = comp[comp["comparison"].str.endswith("vs clean") & (comp["metric"] == "wer")
                 & comp["A"].str.split("/").str[0].isin([s for s in series if "+" not in s]) & comp["lang"].isin(langs)].copy()
        if len(x):
            x["model"] = x["A"].str.split("/").str[0]
            x["cell"] = [f"{d*100:+.1f}{' *' if v != 'no significant change' else ''}" for d, v in zip(x["diff"], x["verdict"])]
            p = x.pivot_table(index=["model", "lang"], columns="condition", values="cell", aggfunc="first")
            st.dataframe(p[[c for c in CONDS if c in p.columns]], width="stretch")
            st.caption("WER points vs clean; * = significant (paired bootstrap, 95% CI excludes 0).")
    with st.expander("All paired significance tests"):
        st.dataframe(comp[comp["lang"].isin(langs)] if len(comp) else comp, hide_index=True, width="stretch")

# ---------------------------------------------------------------- 4. listen
with tabs[3]:
    st.subheader("Listen and compare")
    c1, c2, c3 = st.columns(3)
    lang = c1.selectbox("Language", sorted(scored["lang"].unique()), format_func=lambda l: LANG_NAMES.get(l, l),
                        index=sorted(scored["lang"].unique()).index("hinglish") if "hinglish" in set(scored["lang"]) else 0)
    clip = c2.selectbox("Clip", sorted(scored[scored["lang"] == lang]["clip_id"].unique()))
    cond = c3.selectbox("Condition", CONDS, index=len(CONDS) - 1)
    a1, a2, a3 = st.columns(3)
    for col, label, p in ((a1, "Clean", path("degraded") / "clean" / f"{clip}.wav"),
                          (a2, f"Degraded: {cond}", path("degraded") / cond / f"{clip}.wav"),
                          (a3, "Denoised", path("enhanced") / cond / f"{clip}.wav")):
        col.caption(label)
        col.audio(str(p)) if p.exists() else col.write("(benchmark audio isn't hosted: clone the repo and run degrade/enhance to listen)")
    rows = scored[(scored["clip_id"] == clip) & (scored["condition"] == cond)]
    if len(rows):
        st.markdown(f"**Reference:** {mark(rows.iloc[0]['reference'])}", unsafe_allow_html=True)
        out = ["<table style='width:100%;font-size:14px'><tr><th align=left>system</th><th align=left>transcript "
               "(amounts/dates highlighted)</th><th align=left>after entity repair</th><th>WER</th><th>entities</th></tr>"]
        for r in rows.sort_values(["model", "variant"]).itertuples():
            rep = r.hyp_repaired if isinstance(r.hyp_repaired, str) else repair(r.hypothesis)
            ent = "" if pd.isna(r.entity_hit_rate) else f"{r.entity_hit_rate:.0%} → {r.entity_hit_rate_rep:.0%}"
            out.append(f"<tr><td>{html.escape(r.model)}<br><small>{html.escape(r.variant)}</small></td>"
                       f"<td>{mark(r.hypothesis)}</td><td>{mark(rep) if rep != r.hypothesis else '<small>(unchanged)</small>'}</td>"
                       f"<td align=center>{pct(r.wer)}</td><td align=center>{ent}</td></tr>")
        st.markdown("".join(out) + "</table>", unsafe_allow_html=True)

@st.cache_data
def benchmark_profiles() -> pd.DataFrame:
    """From the local degraded benchmark audio if present, else the committed snapshot (hosted deployments)."""
    from shorgul.health.check import condition_profiles
    prof = condition_profiles(path("degraded"), CONDS)
    snap = path("results") / "condition_profiles.csv"
    return prof if len(prof) or not snap.exists() else pd.read_csv(snap)


# ---------------------------------------------------------------- 5. try your audio
with tabs[4]:
    st.subheader("Try your own audio")
    st.markdown("Upload one clip (≤ 30 s). The **health check is free** and runs instantly. Transcribing the "
                "original plus 4 simulated call conditions costs **5 Gnani calls** with your own key, or 0 in mock mode.")
    up = st.file_uploader("Audio file", type=["wav", "flac", "ogg", "mp3"])
    c1, c2, c3 = st.columns(3)
    t_lang = c1.selectbox("Language ", ["hinglish", "hi", "bn", "ta"])
    t_model = c2.selectbox("Model", ["prisma-v3.0", "prisma-v2.5"])
    t_mock = c3.toggle("Mock mode (no API)", value=True)
    key = "" if t_mock else st.text_input("Your Gnani API key", type="password",
                                          help="Used for these 5 requests only. Held in memory, never written to disk, "
                                               "logs or the cache.")
    if up is not None:
        from shorgul.audit.quick import conditions_available, load_clip, quick_audit
        from shorgul.degrade.pipeline import load_noises
        from shorgul.health.check import check, nearest_condition
        try:
            audio = load_clip(up.getvalue())
        except Exception as e:  # noqa: BLE001 - show any decode/length problem to the user
            st.error(str(e))
            st.stop()
        st.audio(up.getvalue())
        h = check(audio)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SNR estimate", f"{h.snr_db:.0f} dB")
        m2.metric("Energy > 4.2 kHz", "wideband" if h.hf_ratio >= 3e-4 else "narrowband (phone)")
        m3.metric("Packet-loss gaps", f"{h.dropout_pct:.1f}%")
        m4.metric("Nearest benchmark condition", nearest_condition(h, benchmark_profiles()))
        noises = load_noises()
        conds = conditions_available(noises)
        n_calls = 0 if t_mock else 1 + len(conds)
        if st.button(f"Run original + {len(conds)} conditions (up to {n_calls} billed calls)",
                     disabled=(not t_mock and not key)):
            with st.spinner("Transcribing..."):
                res = quick_audit(audio, t_lang, t_model, mock=t_mock, key=key or None, noises=noises)
            st.metric("Stability grade (Prisma-calibrated)", res.grade,
                      f"{res.mean_stability:.1%} mean transcript change · {res.billed_calls} billed calls",
                      delta_color="off")
            for r in res.rows:
                with st.container(border=True):
                    st.markdown(f"**{r['condition']}**" + (f" · stability {r['stability']:.1%}" if "stability" in r else "")
                                + f" · {r['status']}")
                    st.audio(r["audio"])
                    st.markdown(mark(r["transcript"]), unsafe_allow_html=True)
                    if r["repaired"] != r["transcript"]:
                        st.markdown("after entity repair: " + mark(r["repaired"]), unsafe_allow_html=True)
            if t_mock:
                st.warning("Mock mode: transcripts are synthetic.")

# ---------------------------------------------------------------- 6. sample audit
with tabs[5]:
    st.subheader("Sample audit report (`shorgul audit <folder>`)")
    reports = sorted((path("results") / "audits").glob("*/report.html"))
    if reports:
        names = [p.parent.name for p in reports]
        default = names.index("sample_hindi_v3") if "sample_hindi_v3" in names else 0
        pick = st.selectbox("Report", names, index=default)
        st.caption("Each report is one self-contained HTML file (charts and audio embedded) you can email to a customer.")
        components.html(reports[names.index(pick)].read_text(encoding="utf-8"), height=1500, scrolling=True)
    else:
        st.info("No reports yet: `python -m shorgul.cli audit <folder> --lang hi --mock`")

# ---------------------------------------------------------------- 7. method
with tabs[6]:
    st.subheader("Method & limitations")
    st.markdown("""
**Data.** FLEURS test split, 25 clips each for Hindi, Bengali and Tamil (≤ 25 s, one per sentence), plus 25 Hinglish
call-centre lines written for this benchmark and voiced with Gnani Timbre v2.5 (4 voices).

**Conditions.** Noise at the caller (DEMAND street traffic; public square + cafeteria for "market") at a target
acoustic SNR measured on active speech, then 300–3400 Hz band-pass → 8 kHz G.711 μ-law → 16 kHz, then 5% random 20 ms
packet loss. Every clip × condition is deterministic (seed = sha256(clip | condition)).

**Metrics.** Corpus WER/CER after NFC, native-digit → ASCII, punctuation/danda/₹ removal, Devanagari nukta and
chandrabindu folding. Hinglish is compared after romanization; **currency-neutral WER** drops ₹/रुपये words from both
sides. Entity accuracy = share of reference ₹ amounts/dates reproduced in written form.

**Statistics.** 95% percentile bootstrap over clips (1,000 resamples). Every model-vs-model claim is a paired cluster
bootstrap (clips resampled with all their conditions). "Significant" = CI excludes 0.

**Stability.** CER(original transcript, degraded transcript), no reference needed. Validated on FLEURS: per-folder
Spearman ρ = 0.59 for Prisma (p = 0.00015), with points near y = x. **Not calibrated for Whisper.**

**Limitations.**
- **Small n:** 25 clips per language. Many differences are honestly reported as ties.
- **Hinglish is synthetic** (TTS), so real callers have accents, disfluencies and crosstalk the TTS doesn't.
  Denoising helped v3.0 only on this synthetic set.
- **Simulated telephony:** no real network traces, no AMR/Opus codecs (yet), no echo or AGC.
- **Romanized WER is approximate** (`लोन` → `lon` ≠ `loan`); that's why entity accuracy is the Hinglish headline.
- The Prisma v2.5 `en-IN` setting followed the original project spec; it's kept on purpose as the
  "default-style config" example.
""")
