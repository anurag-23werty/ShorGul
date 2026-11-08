"""Build (clip x condition x variant x model) jobs, answer from cache or call the backend.

Billed backends stop at `max_calls` new requests. Output: results/[mock/]hyps.parquet
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from shorgul.asr.base import ASRBackend, MockASR
from shorgul.asr.cache import Cache, asr_key
from shorgul.config import load_config, path

MODELS = ["prisma-v2.5", "prisma-v3.0", "whisper-small"]
VARIANTS = ["raw", "denoised", "context", "matched"]
KEY_COLS = ["clip_id", "condition", "variant", "model"]


@dataclass
class Job:
    row: dict
    condition: str
    variant: str
    model: str
    audio_path: Path
    params: dict[str, Any]


def audio_path_for(clip_id: str, condition: str, variant: str) -> Path:  # matched/context use raw audio
    base = path("enhanced") if variant == "denoised" else path("degraded")
    return base / condition / f"{clip_id}.wav"


def params_for(model: str, row: dict, variant: str) -> dict[str, Any]:
    asr = load_config()["asr"]
    lang = row["lang"]
    if model == "whisper-small":
        return {"language": asr["whisper_langs"][lang], "beam_size": 5}
    p: dict[str, Any] = {
        "language_code": asr["lang_codes"][model][lang],
        "format": "transcribe" if row["has_entities"] in (True, "True") else "verbatim",
    }
    if variant == "matched":  # identical config for both Prisma models (Phase A finding check)
        return {"language_code": "hi-IN", "format": "transcribe"}
    if variant == "context":
        ctx = asr["context"]
        p["topic"] = ctx["topic"]
        p["keyterms"] = json.dumps(ctx["keyterms"], ensure_ascii=False)
    return p


def applies(model: str, variant: str, condition: str, row: dict) -> bool:
    cfg = load_config()
    if variant == "denoised":
        return condition in cfg["noisy_conditions"]
    if variant == "context":
        return model == "prisma-v3.0" and row["lang"] == "hinglish"
    if variant == "matched":
        return model.startswith("prisma") and row["lang"] == "hinglish"
    return True


def build_jobs(manifest: pd.DataFrame, models: list[str], conditions: list[str],
               variants: list[str]) -> list[Job]:
    jobs = []
    for row in manifest.to_dict("records"):
        for cond in conditions:
            for var in variants:
                for model in models:
                    if applies(model, var, cond, row):
                        jobs.append(Job(row, cond, var, model, audio_path_for(row["clip_id"], cond, var),
                                        params_for(model, row, var)))
    return jobs


def make_backend(model: str, mock: bool) -> ASRBackend:
    if mock:
        return MockASR(model)
    if model.startswith("prisma"):
        from shorgul.asr.prisma import PrismaASR
        return PrismaASR(model)
    from shorgul.asr.whisper_local import WhisperASR
    return WhisperASR()


def results_dir(mock: bool) -> Path:
    return path("results") / ("mock" if mock else "")


def _log_error(job: Job, res, mock: bool) -> None:
    """Persist failed-call details (server message only; the API key is never part of res.raw)."""
    out = results_dir(mock) / "errors.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    rec = {"clip_id": job.row["clip_id"], "condition": job.condition, "variant": job.variant,
           "model": job.model, "status": res.status, "detail": res.raw}
    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run_jobs(jobs: list[Job], mock: bool, max_calls: int, dry_run: bool = False,
             backends: dict[str, ASRBackend] | None = None, cache: Cache | None = None) -> pd.DataFrame:
    cache = cache or Cache.default(mock)
    backends = backends if backends is not None else {}
    rows, calls, missing, skipped = [], 0, 0, 0
    plan: dict[str, list[int]] = {}
    for i, job in enumerate(jobs):
        if not job.audio_path.exists():
            missing += 1
            continue
        audio = job.audio_path.read_bytes()
        key = asr_key(audio, job.model, job.params)
        hit = cache.get(key)
        stats = plan.setdefault(job.model, [0, 0])
        stats[0 if hit else 1] += 1
        if dry_run:
            continue
        if hit is None:
            backend = backends.get(job.model) or backends.setdefault(job.model, make_backend(job.model, mock))
            if backend.billed and calls >= max_calls:
                skipped += 1
                continue
            # mock backends need text to corrupt: audits without references pass a placeholder (mock_text)
            extra = {"_reference": job.row.get("mock_text") or job.row["reference"], "_condition": job.condition,
                     "_variant": job.variant}
            res = backend.transcribe(audio, {**job.params, **extra})
            calls += backend.billed
            if res.cacheable:
                cache.put(key, job.model, job.params, {"transcript": res.transcript, "raw": res.raw},
                          res.status, res.latency_s)
            if not res.status.startswith("ok"):
                _log_error(job, res, mock)
            hit = {"response": {"transcript": res.transcript}, "status": res.status, "latency_s": res.latency_s}
            print(f"[run] {i + 1}/{len(jobs)} {job.model} {job.row['clip_id']} {job.condition}/{job.variant}"
                  f" -> {res.status} ({res.latency_s}s)")
        r = job.row
        rows.append({"clip_id": r["clip_id"], "lang": r["lang"], "source": r["source"],
                     "condition": job.condition, "variant": job.variant, "model": job.model,
                     "reference": r["reference"], "entities": r["entities"],
                     "hypothesis": hit["response"].get("transcript", ""),
                     "latency_s": hit["latency_s"], "status": hit["status"], "cache_key": key})
    for model, (cached, new) in plan.items():
        print(f"[plan] {model}: {cached} cached, {new} need a call")
    if missing:
        print(f"[run] {missing} jobs skipped: audio missing (run degrade/enhance first)")
    if skipped:
        print(f"[run] {skipped} billed jobs NOT run: --max-calls {max_calls} reached")
    if not dry_run:
        print(f"[run] new billed calls this run: {calls}")
    return pd.DataFrame(rows)


def save_hyps(df: pd.DataFrame, mock: bool) -> Path:
    out = results_dir(mock) / "hyps.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and len(df):
        old = pd.read_parquet(out)
        old = old.merge(df[KEY_COLS], on=KEY_COLS, how="left", indicator=True)
        df = pd.concat([old[old["_merge"] == "left_only"].drop(columns="_merge"), df], ignore_index=True)
    elif out.exists():
        df = pd.read_parquet(out)
    df.to_parquet(out, index=False)
    return out
