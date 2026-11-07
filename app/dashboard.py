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
clean = view[view["condition"] == "clean"].groupby("series")["wer"].mean()
worst = view[view["condition"] == "market_0"].groupby("series")["wer"].mean()
tiles = st.columns(max(len(clean), 1))
for col, (s, w) in zip(tiles, clean.items()):
    col.metric(f"{s}: clean WER", f"{w:.1%}",
               delta=f"{worst.get(s, float('nan')) - w:+.1%} at market_0", delta_color="inverse")

# --- WER vs condition ---------------------------------------------------------
st.subheader("WER by condition")
metric = st.radio("Metric", ["wer", "cer"], horizontal=True, format_func=str.upper)
line = (alt.Chart(view).mark_line(point=alt.OverlayMarkDef(size=60, filled=True), strokeWidth=2)
        .encode(x=alt.X("condition:N", sort=CONDS, title=None),
                y=alt.Y(f"{metric}:Q", title=metric.upper(), axis=alt.Axis(format="%")),
                color=alt.Color("series:N", scale=COLOR, title="Model"),
                tooltip=["lang", "series", "condition", alt.Tooltip(f"{metric}:Q", format=".1%"),
                         alt.Tooltip("entity_hit_rate:Q", format=".0%"), "n",
                         alt.Tooltip("runaway_rate:Q", format=".0%", title="runaway")])
        .properties(height=260, width=260)
        .facet(column=alt.Column("lang:N", title=None, sort=list(LANG_NAMES))))
st.altair_chart(line)

# --- Hinglish entities ---------------------------------------------------------
ent = view[(view["lang"] == "hinglish") & view["entity_hit_rate"].notna()]
if len(ent):
    st.subheader("Hinglish call-centre: did the ₹ amount and date survive?")
    bars = (alt.Chart(ent).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(x=alt.X("condition:N", sort=CONDS, title=None), xOffset="series:N",
                    y=alt.Y("entity_hit_rate:Q", title="Entity hit rate", scale=alt.Scale(domain=[0, 1]),
                            axis=alt.Axis(format="%")),
                    color=alt.Color("series:N", scale=COLOR, title="Model"),
                    tooltip=["series", "condition", alt.Tooltip("entity_hit_rate:Q", format=".0%"), "n"])
            .properties(height=280))
    st.altair_chart(bars, width="stretch")

with st.expander("Summary table"):
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
