"""Long-audio check: a real ~70 s call built from 14 consecutive Hinglish lines (0.6 s pauses between them),
transcribed through the chunked path, scored against all 14 lines' amounts and dates.

  .venv/bin/python scripts/long_audio_check.py --max-calls 0      # dry: shows chunks + planned calls
  .venv/bin/python scripts/long_audio_check.py --max-calls 4      # real (Prisma v3.0)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shorgul.asr.cache import Cache, asr_key  # noqa: E402
from shorgul.asr.chunk import chunks, split_points, wav_bytes  # noqa: E402
from shorgul.asr.runner import Job, params_for, run_jobs  # noqa: E402
from shorgul.audio import SR, read_wav, write_wav  # noqa: E402
from shorgul.entities.repair import repair  # noqa: E402
from shorgul.metrics.entities import entity_hit_rate  # noqa: E402
from shorgul.metrics.wer_cer import wer_cer  # noqa: E402

IDS = [f"hg_{i:03d}" for i in range(14)]
OUT = ROOT / "data" / "long" / "long_hg_000_013.wav"


def build() -> tuple[np.ndarray, list[tuple[int, int]], pd.DataFrame]:
    m = pd.read_csv(ROOT / "data" / "manifest.csv", keep_default_na=False).set_index("clip_id").loc[IDS]
    rng = np.random.default_rng(0)
    parts, gaps, pos = [], [], 0
    for cid in IDS:
        x = read_wav(ROOT / "data" / "clean" / f"{cid}.wav")
        parts.append(x); pos += len(x)
        gap = (0.0005 * rng.standard_normal(int(0.6 * SR))).astype(np.float32)   # a pause, not digital silence
        gaps.append((pos, pos + len(gap))); parts.append(gap); pos += len(gap)
    return np.concatenate(parts), gaps, m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-calls", type=int, default=0)
    a = ap.parse_args()
    x, gaps, m = build()
    write_wav(OUT, x)
    cuts = split_points(x)
    in_gap = [any(g0 <= c <= g1 for g0, g1 in gaps) for c in cuts]
    print(f"[long] {len(x) / SR:.1f} s, {len(cuts) + 1} chunks "
          f"({', '.join(f'{len(c) / SR:.1f}s' for c in chunks(x))}); cuts inside a pause: {sum(in_gap)}/{len(cuts)}")
    ref = " ".join(m["reference"]); ents = ";".join(e for e in m["entities"] if e)
    row = {"clip_id": "long_hg_000_013", "lang": "hinglish", "source": "long", "reference": ref,
           "entities": ents, "has_entities": True}
    job = Job(row, "clean", "raw", "prisma-v3.0", OUT, params_for("prisma-v3.0", row, "raw"))
    cache = Cache.default()
    need = sum(cache.get(asr_key(wav_bytes(c), "prisma-v3.0", job.params)) is None for c in chunks(x))
    print(f"[long] Prisma v3.0: {need} chunk(s) need a billed call (cap {a.max_calls})")
    if a.max_calls < need:
        return
    df = run_jobs([job], mock=False, max_calls=a.max_calls)
    hyp = df.iloc[0]["hypothesis"]
    # compare with the same 14 lines transcribed one by one (already cached from the benchmark)
    sc = pd.read_parquet(ROOT / "results" / "scored_full.parquet")
    per = sc[(sc.clip_id.isin(IDS)) & (sc.model == "prisma-v3.0") & (sc.variant == "raw") & (sc.condition == "clean")]
    out = {"seconds": round(len(x) / SR, 1), "chunks": len(cuts) + 1, "cuts_in_pause": f"{sum(in_gap)}/{len(cuts)}",
           "entities": len(ents.split(";")),
           "entity_acc_long": round(entity_hit_rate(ents, hyp), 4),
           "entity_acc_long_repaired": round(entity_hit_rate(ents, repair(hyp)), 4),
           "entity_acc_per_clip_mean": round(float(per.entity_hit_rate.mean()), 4),
           "wer_long": round(wer_cer(ref, hyp, "hinglish")[0], 4),
           "wer_per_clip_corpus": round(float((per.word_err.sum()) / per.ref_words.sum()), 4)}
    (ROOT / "results" / "long_audio_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
