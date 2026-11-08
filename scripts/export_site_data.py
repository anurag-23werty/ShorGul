"""Export everything the site shows into site/public/data.json, plus the two example clips as mp3.

Every number on the site comes from here, and everything here comes from results/ (or from running the real
CLI against the cache with --max-calls 0). Run:  .venv/bin/python scripts/export_site_data.py
"""
from __future__ import annotations

import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shorgul.audio import SR, read_wav  # noqa: E402
from shorgul.config import load_config  # noqa: E402
from shorgul.degrade.codecs import ffmpeg_pipe  # noqa: E402
from shorgul.entities.lexicon import CURRENCY, DAY_WORDS, MONTHS, NUMBERS, SCALES  # noqa: E402
from shorgul.entities.repair import _key, repair  # noqa: E402
from shorgul.metrics.entities import entity_hit, parse_entities  # noqa: E402
from shorgul.stats.bootstrap import ci, paired  # noqa: E402

RES = ROOT / "results"
OUT = ROOT / "site" / "public"
EXAMPLES = ["hg_017", "hg_020"]          # the two clips where noise really costs the generic model the amount
EXAMPLE_COND = "market_10"
SYSTEMS = [  # (id, label, model, variant) for the same-audio Hinglish comparison
    ("v25_en", "Prisma v2.5 · en-IN", "prisma-v2.5", "raw"),
    ("v25_hi", "Prisma v2.5 · hi-IN", "prisma-v2.5", "matched"),
    ("v30", "Prisma v3.0", "prisma-v3.0", "raw"),
    ("whisper", "Whisper-small", "whisper-small", "raw"),
]
NUMBER_WORDS = {w for d, r in NUMBERS.values() for w in d + r} | {w for ws in SCALES.values() for w in ws}


def r4(x: float) -> float | None:
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


def triple(p: tuple[float, float, float]) -> dict:
    return {"value": r4(p[0]), "lo": r4(p[1]), "hi": r4(p[2])}


def comp_row(c: pd.DataFrame, **kw) -> dict | None:
    x = c
    for k, v in kw.items():
        x = x[x[k] == v]
    if x.empty:
        return None
    r = x.iloc[0]
    return {"diff": r4(r["diff"]), "lo": r4(r["lo"]), "hi": r4(r["hi"]), "p": r4(r["p"]),
            "significant": r["verdict"] not in ("tie (not significant)", "no significant change"),
            "verdict": r["verdict"], "n_clips": int(r["n_clips"])}


# ------------------------------------------------------------------ metrics
def rankings(sc: pd.DataFrame) -> dict:
    ok = sc[(sc["lang"] == "hinglish") & sc["status"].str.startswith("ok")]
    out = {"scope": "Hinglish call-centre clips (25 TTS lines), all 8 conditions pooled, same audio for every system",
           "systems": []}
    groups = {}
    for sid, label, model, var in SYSTEMS:
        g = ok[(ok["model"] == model) & (ok["variant"] == var)]
        groups[sid] = g
        out["systems"].append({"id": sid, "label": label, "model": model, "variant": var, "n_rows": len(g),
                               "wer": triple(ci(g, "wer")), "wer_cn": triple(ci(g, "wer_cn")),
                               "entity": triple(ci(g, "entity_hit_rate"))})
    for key, metric, lower_better in (("wer_rank", "wer", True), ("entity_rank", "entity", False)):
        vals = sorted(out["systems"], key=lambda s: s[metric]["value"] * (1 if lower_better else -1))
        for i, s in enumerate(vals):
            s[key] = i + 1
    # are adjacent ranks actually different? paired tests between every pair
    pairs = []
    ids = [s[0] for s in SYSTEMS]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            for metric, col in (("wer", "wer"), ("wer_cn", "wer_cn"), ("entity", "entity_hit_rate")):
                r = paired(groups[a], groups[b], col)
                pairs.append({"a": a, "b": b, "metric": metric, "diff": r4(r.point), "lo": r4(r.lo), "hi": r4(r.hi),
                              "significant": bool(r.significant)})
    out["pairs"] = pairs
    return out


def headline(s: pd.DataFrame, c: pd.DataFrame, sc: pd.DataFrame) -> dict:
    ok = sc[(sc["lang"] == "hinglish") & sc["status"].str.startswith("ok")]

    def pooled(model, var, m):
        return triple(ci(ok[(ok["model"] == model) & (ok["variant"] == var)], m))

    return {
        "framing": "Your eval config picks the winner, not the model.",
        "entity_v25_en": pooled("prisma-v2.5", "raw", "entity_hit_rate"),
        "entity_v25_hi": pooled("prisma-v2.5", "matched", "entity_hit_rate"),
        "entity_v30": pooled("prisma-v3.0", "raw", "entity_hit_rate"),
        "matched_v30_minus_v25": {m: comp_row(c, comparison="v3.0 matched vs v2.5 matched", lang="hinglish",
                                              condition="ALL", metric=m) for m in ("wer", "wer_cn", "entity_hit_rate")},
        "note": "Matched = both models with language_code=hi-IN, format=transcribe. wer_cn = currency-neutral WER "
                "(₹4,500 and 4,500 रुपये score the same).",
    }


def degradation(s: pd.DataFrame, c: pd.DataFrame) -> dict:
    conds = load_config()["conditions"]
    meta = [{"id": k, "snr_db": (v or {}).get("snr_db"), "noise": (v or {}).get("noise"),
             "phone": bool((v or {}).get("phone")), "loss": (v or {}).get("loss"), "codec": (v or {}).get("codec")}
            for k, v in conds.items()]
    series = []
    raw = s[s["variant"] == "raw"]
    for (lang, model), g in raw.groupby(["lang", "model"]):
        if lang == "hinglish_human":
            continue
        g = g.set_index("condition")
        pts = []
        for m in meta:
            if m["id"] in g.index:
                r = g.loc[m["id"]]
                vs_clean = comp_row(c, comparison=f"{m['id']} vs clean", lang=lang, metric="wer",
                                    A=f"{model}/raw@{m['id']}") if m["id"] != "clean" else None
                pts.append({"condition": m["id"], "wer": r4(r["wer"]), "lo": r4(r["wer_lo"]), "hi": r4(r["wer_hi"]),
                            "n": int(r["n"]), "vs_clean": vs_clean})
        series.append({"lang": lang, "model": model, "points": pts})
    return {"conditions": meta, "series": series,
            "note": "Corpus WER with 95% bootstrap CI over 25 clips. vs_clean = paired change vs clean audio."}


def entity_by_condition(s: pd.DataFrame) -> dict:
    """Hinglish entity accuracy per condition per system (25 clips each), for scene captions."""
    out = {}
    for sid, _, model, var in SYSTEMS:
        g = s[(s["lang"] == "hinglish") & (s["model"] == model) & (s["variant"] == var)].set_index("condition")
        out[sid] = {c: {"value": r4(g.loc[c, "entity_hit_rate"]), "lo": r4(g.loc[c, "entity_hit_rate_lo"]),
                        "hi": r4(g.loc[c, "entity_hit_rate_hi"]), "n": int(g.loc[c, "n"])} for c in g.index}
    return out


def repair_block(s: pd.DataFrame, c: pd.DataFrame, sc: pd.DataFrame) -> dict:
    ok = sc[(sc["lang"] == "hinglish") & sc["status"].str.startswith("ok")]
    rows = []
    for sid, label, model, var in SYSTEMS:
        g = ok[(ok["model"] == model) & (ok["variant"] == var)]
        rows.append({"id": sid, "label": label,
                     "entity_raw": triple(ci(g, "entity_hit_rate")), "entity_repaired": triple(ci(g, "entity_rep")),
                     "delta_entity": comp_row(c, comparison="repaired vs raw", lang="hinglish", condition="ALL",
                                              metric="entity_hit_rate", A=f"{model}/{var}+repair"),
                     "delta_wer_cn": comp_row(c, comparison="repaired vs raw", lang="hinglish", condition="ALL",
                                              metric="wer_cn", A=f"{model}/{var}+repair")})
    reg_e = int((sc["entity_hit_rate_rep"] < sc["entity_hit_rate"]).sum())
    reg_w = int((sc["word_err_rep"] > sc["word_err"]).sum())
    return {"systems": rows, "regressions": {"entity": reg_e, "wer": reg_w, "transcripts": int(len(sc))},
            "caveat": "Repair rules were developed on these same transcripts: gains are in-sample. "
                      "The 0-regressions result is the robust claim."}


# ------------------------------------------------------------------ examples
CURRENCY_WORDS = {_key(w) for w in CURRENCY}
ANCHOR_WORDS = {_key(w) for w in DAY_WORDS} | {_key(w) for ws in MONTHS.values() for w in ws}
NUMBER_KEYS = {_key(w) for w in NUMBER_WORDS}


def _span(entity: str, hyp: str) -> tuple[str, str | None]:
    """(state, the words the chip shows) for ONE reference entity in ONE transcript."""
    toks = hyp.split()
    keys = [_key(t) for t in toks]
    digits = re.sub(r"[^\d]", "", entity.split()[0])
    is_amount = entity.startswith("₹")
    anchors = CURRENCY_WORDS if is_amount else ANCHOR_WORDS
    if entity_hit(entity, hyp):
        for i, t in enumerate(toks):
            if re.sub(r"[^\d]", "", t) == digits:
                j = i + 1 if i + 1 < len(toks) and keys[i + 1] in CURRENCY_WORDS else i
                return "written", " ".join(toks[i:j + 1]).strip("।,.")
        return "written", entity
    rep = repair(hyp)
    if entity_hit(entity, rep):
        sm = difflib.SequenceMatcher(a=toks, b=rep.split(), autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "replace" and digits in re.sub(r"[^\d]", "", " ".join(rep.split()[j1:j2])):
                return "spoken", " ".join(toks[i1:i2])
        return "spoken", None
    for i, k in enumerate(keys):  # number words right before this entity's anchor (currency / month / तारीख)
        if k in anchors:
            j = i
            while j > 0 and keys[j - 1] in NUMBER_KEYS:
                j -= 1
            if j < i:
                return "garbled", " ".join(toks[j:i + 1]).strip("।,.")
    return "missing", None


def chip_state(entity: str, hyp: str) -> dict:
    """How a reference amount/date shows up: written / spoken (recoverable) / garbled / missing, + shown words."""
    state, shown = _span(entity, hyp)
    return {"entity": entity, "state": state, "shown": shown, "after_repair": entity_hit(entity, repair(hyp))}


def peaks(x: np.ndarray, bins: int = 480) -> list[float]:
    n = len(x) // bins
    a = np.abs(x[: n * bins]).reshape(bins, n).max(axis=1)
    return [round(float(v), 4) for v in a]


def bands(x: np.ndarray, t_bins: int = 96, edges=(0, 300, 600, 1200, 2000, 3000, 3400, 4500, 6000, 8000)) -> dict:
    """Coarse spectrogram: dB energy per frequency band per time slice (for the band-fading visual)."""
    n = len(x) // t_bins
    frames = x[: n * t_bins].reshape(t_bins, n) * np.hanning(n)
    spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    f = np.fft.rfftfreq(n, 1 / SR)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        e = spec[:, (f >= lo) & (f < hi)].sum(axis=1) + 1e-10
        rows.append([round(float(v), 1) for v in 10 * np.log10(e)])
    return {"edges_hz": list(edges), "db": rows}


def bandpass_only(x: np.ndarray) -> np.ndarray:
    """The 300-3400 Hz band-pass alone (same filters as the phone channel, without 8 kHz mu-law)."""
    bp = "highpass=f=300,highpass=f=300,lowpass=f=3400,lowpass=f=3400"
    y = np.frombuffer(ffmpeg_pipe(x.astype(np.float32), ["-f", "f32le", "-ar", "16000", "-ac", "1"],
                                  ["-af", bp, "-f", "f32le"]), dtype=np.float32)
    return y[: len(x)]


def encode_mp3(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "22050",
                    "-c:a", "libmp3lame", "-b:a", "48k", str(dst)], check=True)


def examples(sc: pd.DataFrame) -> list[dict]:
    out = []
    for cid in EXAMPLES:
        rows = sc[(sc["clip_id"] == cid)]
        ref = rows.iloc[0]["reference"]
        ents = parse_entities(rows.iloc[0]["entities"])
        clean = read_wav(ROOT / "data" / "degraded" / "clean" / f"{cid}.wav")
        band_only = bandpass_only(clean)  # visual stage only (no mu-law); ASR was run on the real conditions below
        stages = {
            "clean": clean,
            "phone": read_wav(ROOT / "data" / "degraded" / "phone" / f"{cid}.wav"),
            EXAMPLE_COND: read_wav(ROOT / "data" / "degraded" / EXAMPLE_COND / f"{cid}.wav"),
        }
        for st in ("clean", EXAMPLE_COND):
            encode_mp3(ROOT / "data" / "degraded" / st / f"{cid}.wav", OUT / "audio" / f"{cid}_{st}.mp3")
        transcripts = []
        for sid, label, model, var in SYSTEMS:
            for cond in ("clean", "phone", EXAMPLE_COND):
                r = rows[(rows["model"] == model) & (rows["variant"] == var) & (rows["condition"] == cond)]
                if r.empty:
                    continue
                h = r.iloc[0]["hypothesis"]
                transcripts.append({"system": sid, "condition": cond, "text": h, "repaired": repair(h),
                                    "wer": r4(r.iloc[0]["wer"]), "entities": [chip_state(e, h) for e in ents]})
        out.append({
            "clip_id": cid, "reference": ref, "entities": ents, "duration_s": round(len(clean) / SR, 2),
            "audio": {"clean": f"audio/{cid}_clean.mp3", EXAMPLE_COND: f"audio/{cid}_{EXAMPLE_COND}.mp3"},
            "waveform": {k: peaks(v) for k, v in stages.items()} | {"bandpass": peaks(band_only)},
            "spectrum": {k: bands(v) for k, v in stages.items()} | {"bandpass": bands(band_only)},
            "transcripts": transcripts,
            "note": f"Real transcripts for clean, phone (300-3400 Hz + 8 kHz mu-law) and {EXAMPLE_COND} "
                    "(market babble at 10 dB acoustic SNR, then the phone channel).",
        })
    return out


# ------------------------------------------------------------------ terminal captures
NOISE = re.compile(r"^\[run\] \d+/\d+|warn|Warning|^\s*$", re.I)


def run_cli(args: list[str], cwd: Path, display: str) -> dict:
    exe = ROOT / ".venv" / "bin" / "shorgul"
    p = subprocess.run([str(exe), *args], cwd=cwd, capture_output=True, text=True)
    text = (p.stdout + p.stderr).replace(str(ROOT) + "/", "").replace(str(cwd) + "/", "./")
    lines = [ln.rstrip() for ln in text.splitlines() if not NOISE.search(ln)]
    return {"command": display, "output": lines[:24], "exit_code": p.returncode}


def terminals() -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="shorgul_site_"))
    try:
        (tmp / "calls").mkdir()
        for p in sorted((ROOT / "data" / "clean").glob("hg_0[01]*.wav"))[:12]:
            shutil.copy(p, tmp / "calls" / p.name)
        (tmp / "customer_calls").mkdir()
        for p in sorted((ROOT / "data" / "clean").glob("hi_0*.wav")):
            shutil.copy(p, tmp / "customer_calls" / p.name)
        out_a = tmp / "out_a"
        out_b = tmp / "out_b"
        voicebot = run_cli(["audit", "./calls", "--lang", "hinglish", "--model", "prisma-v3.0", "--max-calls", "0",
                            "--out", str(out_a)], tmp,
                           "shorgul audit ./calls --lang hinglish --model prisma-v3.0 --max-calls 60")
        solutions = run_cli(["audit", "./customer_calls", "--lang", "hi", "--model", "prisma-v3.0", "--max-calls", "0",
                             "--out", str(out_b)], tmp,
                            "shorgul audit ./customer_calls --lang hi --model prisma-v3.0 --max-calls 125")
        gate = run_cli(["compare", "--baseline", str(RES / "results.parquet"), "--baseline-model", "prisma-v2.5",
                        "--baseline-variant", "matched", "--candidate", str(RES / "results.parquet"),
                        "--candidate-model", "prisma-v3.0", "--candidate-variant", "matched",
                        "--metric", "entity", "--fail-on", "2"], ROOT,
                       "shorgul compare --baseline v25.parquet --candidate v30.parquet --metric entity --fail-on 2")
        gate_wer = run_cli(["compare", "--baseline", str(RES / "results.parquet"), "--baseline-model", "prisma-v2.5",
                            "--candidate", str(RES / "results.parquet"), "--candidate-model", "prisma-v3.0",
                            "--langs", "hi,bn,ta", "--metric", "wer", "--fail-on", "2"], ROOT,
                           "shorgul compare --baseline v25.parquet --candidate v30.parquet --metric wer --fail-on 2")
        for t in (voicebot, solutions):  # captured from cache; the shown --max-calls is what a fresh run needs
            t["output"] = [ln.replace("cap 0", "cap " + t["command"].split()[-1]) for ln in t["output"]
                           if not ln.startswith("[run] new billed") and not ln.startswith("[plan]")
                           and "report ->" not in ln]
        return {"voicebot_golive": voicebot, "solutions_deal": solutions, "release_gate_entity": gate,
                "release_gate_wer": gate_wer,
                "note": "Captured by running the real CLI against the result cache (no API calls). Paths shortened."}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def pipeline_counts(sc: pd.DataFrame) -> dict:
    m = pd.read_csv(ROOT / "data" / "manifest.csv", keep_default_na=False)
    return {"clips": int(len(m[m["lang"] != "hinglish_human"])), "languages": ["hi", "bn", "ta", "hinglish"],
            "conditions": list(load_config()["conditions"]), "models": ["prisma-v2.5", "prisma-v3.0", "whisper-small"],
            "transcripts": int(len(sc)), "failed": int((~sc["status"].str.startswith("ok")).sum()),
            "paired_tests": int(len(pd.read_csv(RES / "comparisons.csv")))}


def main() -> None:
    s = pd.read_csv(RES / "summary.csv")
    c = pd.read_csv(RES / "comparisons.csv")
    sc = pd.read_parquet(RES / "scored_full.parquet")
    sc = sc[sc["lang"] != "hinglish_human"]
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "results/summary.csv, results/comparisons.csv, results/scored_full.parquet, results/finding_check.md",
        "ci": "95% percentile bootstrap over clips, 1,000 resamples; comparisons are paired",
        "headline": headline(s, c, sc),
        "rankings": rankings(sc),
        "entity_by_condition": entity_by_condition(s),
        "systems": [{"id": a, "label": b, "model": m, "variant": v} for a, b, m, v in SYSTEMS],
        "degradation": degradation(s, c),
        "repair": repair_block(s, c, sc),
        "examples": examples(sc),
        "terminals": terminals(),
        "pipeline": pipeline_counts(sc),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    kb = (OUT / "data.json").stat().st_size / 1024
    print(f"[export] site/public/data.json ({kb:.0f} KB), {len(data['examples'])} clips, "
          f"{len(list((OUT / 'audio').glob('*.mp3')))} mp3")


if __name__ == "__main__":
    main()
