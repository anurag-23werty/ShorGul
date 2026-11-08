"""Long-audio support: split calls longer than the 30 s STT limit at natural pauses, transcribe each
chunk (cached and billed individually), and stitch the text back together in order."""
from __future__ import annotations

import io

import numpy as np
import soundfile as sf

from shorgul.audio import SR

LIMIT_S = 30.0       # Gnani STT hard limit per request
TARGET_S = 28.0      # stay safely under it
FRAME = SR * 20 // 1000


def _frame_db(x: np.ndarray) -> np.ndarray:
    n = len(x) // FRAME
    p = np.mean(x[: n * FRAME].reshape(n, FRAME) ** 2, axis=1) + 1e-12
    return 10 * np.log10(p)


def split_points(x: np.ndarray, target_s: float = TARGET_S, min_gap_ms: int = 200) -> list[int]:
    """Sample indices where to cut so every chunk is <= target_s. Prefers the longest pause in the last
    10 s before each limit; falls back to the quietest frame in the last 3 s if the speaker never pauses."""
    if len(x) <= int(target_s * SR):
        return []
    db = _frame_db(x)
    floor = np.percentile(db, 10)
    silent = db < floor + 0.35 * (np.percentile(db, 90) - floor)
    cuts, start = [], 0
    max_f = int(target_s * 1000 / 20)
    while len(db) - start > max_f:
        lo, hi = start + max_f - 500, start + max_f        # search window: last 10 s before the limit
        best, run_len, best_len = None, 0, 0
        for f in range(max(lo, start + 1), hi):
            run_len = run_len + 1 if silent[f] else 0
            if run_len * 20 >= min_gap_ms and run_len >= best_len:
                best, best_len = f - run_len // 2, run_len    # middle of the longest (latest on ties) pause
        if best is None:
            w0 = start + max_f - 150                           # no pause: quietest frame in the last 3 s
            best = w0 + int(np.argmin(db[w0:hi]))
        cuts.append(best * FRAME)
        start = best
    return cuts


def chunks(x: np.ndarray, target_s: float = TARGET_S) -> list[np.ndarray]:
    edges = [0, *split_points(x, target_s), len(x)]
    return [x[a:b] for a, b in zip(edges[:-1], edges[1:]) if b > a]


def wav_bytes(x: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.clip(x, -1, 1), SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def transcribe_any(x: np.ndarray, backend, model: str, params: dict, cache, extra: dict | None = None
                   ) -> tuple[str, str, int]:
    """Transcribe audio of any length: one request if <= the limit, else chunked. Every request cached.
    Returns (text, status, billed_calls)."""
    from shorgul.asr.cache import asr_key
    parts = chunks(x) if len(x) / SR > LIMIT_S else [x]
    texts, statuses, billed = [], [], 0
    for c in parts:
        b = wav_bytes(c)
        k = asr_key(b, model, params)
        hit = cache.get(k)
        if hit is None:
            r = backend.transcribe(b, {**params, **(extra or {})})
            billed += int(getattr(backend, "billed", False))
            if r.cacheable:
                cache.put(k, model, params, {"transcript": r.transcript}, r.status, r.latency_s)
            texts.append(r.transcript); statuses.append(r.status)
        else:
            texts.append(hit["response"].get("transcript", "")); statuses.append(hit["status"])
    status = next((s for s in statuses if not s.startswith("ok")), "ok")
    return stitch(texts), status, billed


def stitch(parts: list[str]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())
