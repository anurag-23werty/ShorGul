"""`shorgul audit <folder>`: grade a customer's own audio for telephony robustness.

For each clip: health check → nearest benchmark condition → transcribe the original and N simulated
call conditions → stability (no reference needed) → entity retention → optional WER/entity accuracy
when refs.csv is supplied. Billed calls = clips × (1 + N conditions), capped by --max-calls.
"""
from __future__ import annotations

import difflib
import html
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from shorgul.asr.cache import Cache
from shorgul.asr.runner import Job, params_for, run_jobs
from shorgul.audio import read_wav, write_wav
from shorgul.audit.stability import GRADES, grade, stability
from shorgul.config import load_config, path
from shorgul.degrade.pipeline import degrade_audio, load_noises
from shorgul.entities.repair import repair
from shorgul.health.check import check, condition_profiles, nearest_condition
from shorgul.metrics.entities import entity_hit_rate
from shorgul.metrics.wer_cer import wer_cer
from shorgul.stats.bootstrap import ci

AUDIO_EXT = {".wav", ".flac", ".ogg", ".mp3"}
DEFAULT_CONDITIONS = ["phone", "loss_5", "traffic_5", "market_0"]  # mild -> harsh
BREAK_AT = 0.05  # mean stability at which the grade drops below B (≈ +5 pts expected WER)
MOCK_TEXT = "नमस्ते सर आपकी loan EMI ₹4,500 की 5 मार्च को due है कृपया समय पर भुगतान करें"


@dataclass
class AuditResult:
    name: str
    lang: str
    model: str
    conditions: list[str]
    clips: pd.DataFrame          # one row per clip
    rows: pd.DataFrame           # one row per clip x condition
    summary: dict = field(default_factory=dict)
    mock: bool = False


def _numbers(text: str) -> set[str]:
    """Digit tokens after entity repair: the amounts/dates a CRM would extract."""
    import re
    return set(re.findall(r"\d[\d,]*", repair(text).replace(",", "")))


def plan_calls(n_clips: int, n_conditions: int) -> int:
    return n_clips * (1 + n_conditions)


def collect(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXT)


def prepare_audio(files: list[Path], out: Path, conditions: list[str], noises: dict) -> pd.DataFrame:
    profiles = condition_profiles(path("degraded"), list(load_config()["conditions"]))
    rows = []
    for f in files:
        clip_id = f.stem
        audio = read_wav(f)
        write_wav(out / "original" / f"{clip_id}.wav", audio)
        h = check(audio)
        for cond in conditions:
            dst = out / cond / f"{clip_id}.wav"
            if not dst.exists():
                write_wav(dst, degrade_audio(audio, clip_id, cond, noises)[0])
        rows.append({"clip_id": clip_id, "file": f.name, **h.as_dict(),
                     "nearest_condition": nearest_condition(h, profiles)})
    return pd.DataFrame(rows)


def run_audit(folder: Path, lang: str, model: str, max_calls: int, mock: bool, out: Path,
              conditions: list[str] | None = None, refs: Path | None = None,
              noises: dict | None = None) -> AuditResult:
    conditions = conditions or DEFAULT_CONDITIONS
    files = collect(folder)
    if not files:
        raise ValueError(f"no audio files in {folder}")
    ref_map = {}
    if refs and refs.exists():
        r = pd.read_csv(refs, keep_default_na=False)
        ref_map = {Path(x).stem: (ref, ents) for x, ref, ents in
                   zip(r["file"], r["reference"], r.get("entities", [""] * len(r)))}
    clips = prepare_audio(files, out, conditions, noises if noises is not None else load_noises())
    jobs = []
    for clip_id in clips["clip_id"]:
        ref, ents = ref_map.get(clip_id, ("", ""))
        row = {"clip_id": clip_id, "lang": lang, "source": "audit", "reference": ref, "entities": ents,
               "has_entities": lang == "hinglish" or bool(ents), "mock_text": ref or MOCK_TEXT}
        params = params_for(model, row, "raw")
        for cond in ["original", *conditions]:
            jobs.append(Job(row, cond, "raw", model, out / cond / f"{clip_id}.wav", params))
    hyps = run_jobs(jobs, mock=mock, max_calls=max_calls, cache=Cache.default(mock))
    if hyps.empty:
        raise RuntimeError("no transcripts: raise --max-calls or use --mock")
    res = _analyse(out.name, lang, model, conditions, clips, hyps)
    res.mock = mock
    return res


def _analyse(name: str, lang: str, model: str, conditions: list[str], clips: pd.DataFrame,
             hyps: pd.DataFrame) -> AuditResult:
    orig = hyps[hyps["condition"] == "original"].set_index("clip_id")["hypothesis"]
    rows = []
    for r in hyps[hyps["condition"] != "original"].itertuples():
        if r.clip_id not in orig.index:
            continue
        o = orig[r.clip_id]
        nums = _numbers(o)
        row = {"clip_id": r.clip_id, "condition": r.condition, "original_hyp": o, "hypothesis": r.hypothesis,
               "stability": stability(o, r.hypothesis, lang),
               "entity_retention": (len(nums & _numbers(r.hypothesis)) / len(nums)) if nums else np.nan,
               "repair_changes": repair(r.hypothesis) != r.hypothesis}
        if r.reference:
            row["wer"] = wer_cer(r.reference, r.hypothesis, lang)[0]
            row["entity_acc"] = entity_hit_rate(r.entities, repair(r.hypothesis))
        rows.append(row)
    rows = pd.DataFrame(rows)
    res = AuditResult(name, lang, model, conditions, clips, rows)
    res.summary = _summary(res, orig)
    return res


def _summary(res: AuditResult, orig: pd.Series) -> dict:
    rows = res.rows
    per_cond = []
    for cond in res.conditions:
        g = rows[rows["condition"] == cond]
        point, lo, hi = ci(g, "stability") if len(g) else (np.nan,) * 3  # bootstrap CI over clips
        ret = rows.loc[rows["condition"] == cond, "entity_retention"]
        per_cond.append({"condition": cond, "stability": point, "lo": lo, "hi": hi, "grade": grade(point),
                         "entity_retention": float(ret.mean()) if ret.notna().any() else np.nan,
                         "entity_n": int(ret.notna().sum())})
    per_cond = pd.DataFrame(per_cond)
    mean_stab = float(rows["stability"].mean())
    breaking = next((r.condition for r in per_cond.itertuples() if r.stability >= BREAK_AT), None)
    bench = _benchmark_expectation(res)
    orig_changed = sum(repair(t) != t for t in orig)
    return {
        "grade": grade(mean_stab), "mean_stability": mean_stab, "per_condition": per_cond,
        "breaking_point": breaking, "n_clips": len(res.clips),
        "nearest": res.clips["nearest_condition"].value_counts().to_dict(),
        "benchmark": bench, "fixes": _fixes(res, orig_changed, len(orig)),
        "worst": _worst(res), "has_refs": "wer" in rows,
    }


def _benchmark_expectation(res: AuditResult) -> list[dict]:
    """Benchmark corpus WER for the conditions this customer's audio most resembles."""
    p = path("results") / "summary.csv"
    if not p.exists():
        return []
    s = pd.read_csv(p)
    s = s[(s["model"] == res.model) & (s["variant"] == "raw")]
    lang = res.lang if res.lang in set(s["lang"]) else None
    out = []
    for cond, n in res.clips["nearest_condition"].value_counts().items():
        g = s[(s["condition"] == cond) & ((s["lang"] == lang) if lang else True)]
        if len(g):
            out.append({"condition": cond, "clips": int(n), "wer": float(g["wer"].mean()),
                        "lo": float(g["wer_lo"].mean()), "hi": float(g["wer_hi"].mean()),
                        "basis": f"{res.model}, {lang or 'mean of benchmark languages'}"})
    return out


def _fixes(res: AuditResult, orig_changed: int, n_orig: int) -> list[dict]:
    """Recommend fixes from (a) this audit's own transcripts and (b) the benchmark's paired tests."""
    fixes = []
    share = orig_changed / max(n_orig, 1)
    fixes.append({"fix": "Entity repair (shorgul.entities.repair)", "recommend": share > 0,
                  "evidence": f"changes {orig_changed}/{n_orig} of your transcripts (spoken numbers or split dates "
                              f"→ written form). Benchmark: 0 regressions on 4,175 transcripts; "
                              f"Prisma v2.5 en-IN entity accuracy 0% → 100% (in-sample, 25 clips)."})
    comp = path("results") / "comparisons.csv"
    den = ctx = None
    if comp.exists():
        c = pd.read_csv(comp)
        d = c[(c["comparison"] == f"{res.model} denoised vs raw") & (c["condition"] == "ALL") & (c["metric"] == "wer")
              & (c["lang"] != "hinglish")]
        if len(d):
            hurt = (d["verdict"].str.contains("raw better")).sum()
            den = f"benchmark: denoising raised {res.model}'s WER significantly in {hurt}/{len(d)} languages on real speech."
        x = c[(c["comparison"] == "v3.0 context vs v3.0 raw") & (c["condition"] == "ALL") & (c["metric"] == "wer")]
        if len(x):
            r = x.iloc[0]
            ctx = f"benchmark: Δ WER {r['diff'] * 100:+.1f} pts [{r.lo * 100:+.1f}, {r.hi * 100:+.1f}], {r.verdict}."
    fixes.append({"fix": "Generic denoiser (spectral gating)", "recommend": False,
                  "evidence": den or "benchmark: hurts Prisma on real speech."})
    fixes.append({"fix": "Prisma v3.0 context hints (topic + keyterms)", "recommend": None,
                  "evidence": (ctx or "benchmark: not significant on 25 clips.") +
                              " Worth a try for domain vocabulary; not proven to move WER."})
    if res.lang == "hinglish" and res.model == "prisma-v2.5":
        fixes.insert(0, {"fix": "Use language_code=hi-IN, not en-IN", "recommend": True,
                         "evidence": "benchmark: Prisma v2.5 entity accuracy 0% (en-IN) → 94% (hi-IN) on the same audio."})
    return fixes


def _diff_html(a: str, b: str) -> str:
    aw, bw = a.split(), b.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=aw, b=bw, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(html.escape(" ".join(aw[i1:i2])))
        if op in ("delete", "replace"):
            out.append(f"<del>{html.escape(' '.join(aw[i1:i2]))}</del>")
        if op in ("insert", "replace"):
            out.append(f"<ins>{html.escape(' '.join(bw[j1:j2]))}</ins>")
    return " ".join(out)


def _worst(res: AuditResult, k: int = 3) -> list[dict]:
    per_clip = res.rows.groupby("clip_id")["stability"].mean().sort_values(ascending=False).head(k)
    out = []
    for clip_id, s in per_clip.items():
        g = res.rows[res.rows["clip_id"] == clip_id].sort_values("stability", ascending=False).iloc[0]
        out.append({"clip_id": clip_id, "mean_stability": float(s), "condition": g["condition"],
                    "stability": float(g["stability"]), "original": g["original_hyp"], "degraded": g["hypothesis"],
                    "diff": _diff_html(g["original_hyp"], g["hypothesis"])})
    return out


GRADE_TEXT = {g: t for g, t in zip([g for _, g in GRADES], [
    "Robust: transcripts barely change under simulated call conditions (≈ < +2 pts WER).",
    "Good: small changes (≈ +2–5 pts WER).",
    "Fragile under harsh conditions (≈ +5–10 pts WER).",
    "Unreliable on noisy calls (≈ +10–20 pts WER).",
    "Breaks on phone audio (≈ > +20 pts WER)."])}
