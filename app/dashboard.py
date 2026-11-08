"""ShorGul Bench dashboard: streamlit run app/dashboard.py"""
from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shorgul.config import load_config, path  # noqa: E402
from shorgul.metrics.charts import LANG_NAMES, SERIES_COLORS  # noqa: E402

st.set_page_config(page_title="ShorGul Bench", layout="wide")
CONDS = list(load_config()["conditions"])
COLOR = alt.Scale(domain=list(SERIES_COLORS), range=list(SERIES_COLORS.values()))


@st.cache_data
def load(mock: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    rdir = path("results") / ("mock" if mock else "")
    scored = pd.read_parquet(rdir / "scored_full.parquet")
    summary = pd.read_csv(rdir / "summary.csv")
    for df in (scored, summary):
        df["series"] = df["model"] + df["variant"].map({"context": " + context"}).fillna("")
    return scored, summary


st.title("ShorGul Bench")
st.caption("How Indian-language ASR degrades on simulated phone-call audio: "
           "band-limit → 8 kHz μ-law → packet loss → street/market noise.")

real_ok = (path("results") / "summary.csv").exists()
mock_ok = (path("results") / "mock" / "summary.csv").exists()
if not (real_ok or mock_ok):
    st.error("No results yet. Run `python -m shorgul.cli score` (or `score --mock`).")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
source = c1.radio("Data", [s for s, ok in (("real", real_ok), ("mock", mock_ok)) if ok], horizontal=True)
scored, summary = load(source == "mock")
langs = c2.multiselect("Language", sorted(summary["lang"].unique()), default=sorted(summary["lang"].unique()),
                       format_func=lambda l: LANG_NAMES.get(l, l))
series = c3.multiselect("Model", list(SERIES_COLORS), default=[s for s in SERIES_COLORS if s in set(summary["series"])])
variant = c4.radio("Audio", ["raw", "denoised"], horizontal=True,
                   help="denoised = spectral gating applied to the received phone audio")

view = summary[summary["lang"].isin(langs) & summary["series"].isin(series)]
view = view[(view["variant"] == variant) | (view["variant"] == "context")]
if source == "mock":
    st.warning("MOCK data: synthetic transcripts for pipeline testing, not real model output.")

# --- headline tiles -----------------------------------------------------------
# Like-for-like only: FLEURS languages (same sentences for every model), raw/denoised variant.
fleurs = view[(view["lang"] != "hinglish") & (view["variant"] == variant)]
clean = fleurs[fleurs["condition"] == "clean"].groupby("series")["wer"].mean()
worst = fleurs[fleurs["condition"] == "market_0"].groupby("series")["wer"].mean()
if len(clean):
    st.caption("Mean WER over the selected FLEURS languages (Hindi/Bengali/Tamil): clean, and change at market_0")
    tiles = st.columns(len(clean))
    for col, (s, w) in zip(tiles, clean.items()):
        col.metric(s, f"{w:.1%}", delta=f"{worst.get(s, float('nan')) - w:+.1%} at market_0",
                   delta_color="inverse")

# --- WER vs condition ---------------------------------------------------------
st.subheader("WER by condition")
metric = st.radio("Metric", ["wer", "cer"], horizontal=True, format_func=str.upper)
st.caption("Shaded band = 95% bootstrap CI over clips. Model-vs-model verdicts use paired tests: see the table below.")
base = alt.Chart(view).encode(
    x=alt.X("condition:N", sort=CONDS, title=None),
    color=alt.Color("series:N", scale=COLOR, title="Model"))
band = base.mark_area(opacity=0.15).encode(y=alt.Y(f"{metric}_lo:Q"), y2=f"{metric}_hi:Q")
pts = base.mark_line(point=alt.OverlayMarkDef(size=60, filled=True), strokeWidth=2).encode(
    y=alt.Y(f"{metric}:Q", title=f"{metric.upper()} (band = 95% CI)", axis=alt.Axis(format="%")),
    tooltip=["lang", "series", "condition", alt.Tooltip(f"{metric}:Q", format=".1%"),
             alt.Tooltip(f"{metric}_lo:Q", format=".1%", title="95% CI low"),
             alt.Tooltip(f"{metric}_hi:Q", format=".1%", title="95% CI high"), "n",
             alt.Tooltip("runaway_rate:Q", format=".0%", title="runaway")])
line = (band + pts).properties(height=260, width=260).facet(
    column=alt.Column("lang:N", title=None, sort=list(LANG_NAMES)))
st.altair_chart(line)

# --- Hinglish entities ---------------------------------------------------------
ent = view[(view["lang"] == "hinglish") & view["entity_hit_rate"].notna()]
if len(ent):
    st.subheader("Hinglish call-centre: did the ₹ amount and date survive?")
    eb = alt.Chart(ent).encode(x=alt.X("condition:N", sort=CONDS, title=None), xOffset="series:N")
    bars = (eb.mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                y=alt.Y("entity_hit_rate:Q", title="Entity hit rate (whiskers = 95% CI)",
                        scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
                color=alt.Color("series:N", scale=COLOR, title="Model"),
                tooltip=["series", "condition", alt.Tooltip("entity_hit_rate:Q", format=".0%"),
                         alt.Tooltip("entity_hit_rate_lo:Q", format=".0%", title="95% CI low"),
                         alt.Tooltip("entity_hit_rate_hi:Q", format=".0%", title="95% CI high"), "n"])
            + eb.mark_rule(color="#52514e").encode(y="entity_hit_rate_lo:Q", y2="entity_hit_rate_hi:Q")
            ).properties(height=280)
    st.altair_chart(bars, width="stretch")

comp_path = path("results") / ("mock" if source == "mock" else "") / "comparisons.csv"
if comp_path.exists():
    with st.expander("Paired significance tests (A − B, 95% CI)"):
        comp = pd.read_csv(comp_path)
        comp = comp[comp["lang"].isin(langs)]
        st.dataframe(comp, width="stretch", hide_index=True)

with st.expander("Summary table (with 95% CIs)"):
    st.dataframe(view.drop(columns=["series"]), width="stretch", hide_index=True)

# --- clip explorer ------------------------------------------------------------
st.subheader("Listen and compare")
e1, e2 = st.columns([1, 1])
clips = sorted(scored[scored["lang"].isin(langs)]["clip_id"].unique())
clip = e1.selectbox("Clip", clips)
cond = e2.selectbox("Condition", CONDS, index=len(CONDS) - 1)
a1, a2, a3 = st.columns(3)
for col, label, p in ((a1, "Clean", path("degraded") / "clean" / f"{clip}.wav"),
                      (a2, f"Degraded: {cond}", path("degraded") / cond / f"{clip}.wav"),
                      (a3, "Denoised", path("enhanced") / cond / f"{clip}.wav")):
    col.caption(label)
    if p.exists():
        col.audio(str(p))
    else:
        col.write("—")
rows = scored[(scored["clip_id"] == clip) & (scored["condition"] == cond)]
if len(rows):
    st.markdown(f"**Reference:** {rows.iloc[0]['reference']}")
    st.dataframe(rows[["series", "variant", "hypothesis", "wer", "cer", "entity_hit_rate", "status"]],
                 width="stretch", hide_index=True)

# --- worst cases ---------------------------------------------------------------
with st.expander("Worst 20 transcripts in current filter"):
    w = scored[scored["lang"].isin(langs) & scored["series"].isin(series)].nlargest(20, "wer")
    st.dataframe(w[["clip_id", "condition", "series", "variant", "wer", "reference", "hypothesis"]],
                 width="stretch", hide_index=True)
