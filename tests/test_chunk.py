import numpy as np

from shorgul.asr.base import ASRResult
from shorgul.asr.cache import Cache
from shorgul.asr.chunk import LIMIT_S, chunks, split_points, stitch, wav_bytes
from shorgul.asr.runner import Job, run_jobs
from shorgul.audio import SR


def _speechy(seconds: float, pause_every: float = 4.0, seed: int = 0) -> np.ndarray:
    """Bursts of 'speech' with a 0.5 s pause every `pause_every` seconds, plus a mic noise floor."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    x = 0.2 * rng.standard_normal(n).astype(np.float32)
    period, gap = int(pause_every * SR), int(0.5 * SR)
    for s in range(period - gap, n, period):
        x[s:s + gap] *= 0.01
    return x + 0.001 * rng.standard_normal(n).astype(np.float32)


def test_short_audio_is_not_split():
    assert split_points(_speechy(20)) == [] and len(chunks(_speechy(20))) == 1


def test_long_audio_splits_under_limit_at_pauses():
    x = _speechy(95)
    parts = chunks(x)
    assert len(parts) >= 4
    assert all(len(p) / SR <= 28.0 + 1e-6 for p in parts)
    assert sum(len(p) for p in parts) == len(x)            # nothing lost, nothing duplicated
    for c in split_points(x):                               # every cut lands inside a quiet stretch
        assert np.abs(x[c - 160:c + 160]).max() < 0.05


def test_no_pauses_still_respects_limit():
    x = (0.2 * np.random.default_rng(1).standard_normal(int(70 * SR))).astype(np.float32)
    assert all(len(p) / SR <= 28.0 + 1e-6 for p in chunks(x))


def test_stitch():
    assert stitch(["नमस्ते सर", " ", "आपकी EMI ₹4,500 है"]) == "नमस्ते सर आपकी EMI ₹4,500 है"


class Counting:
    billed, name = True, "prisma-v3.0"

    def __init__(self):
        self.n = 0

    def transcribe(self, audio, params):
        self.n += 1
        return ASRResult(f"part{self.n}", "ok", 0.1)


def test_runner_chunks_long_clip_caches_and_caps(tmp_path):
    p = tmp_path / "long.wav"
    p.write_bytes(wav_bytes(_speechy(70)))
    row = {"clip_id": "long", "lang": "hi", "source": "x", "reference": "r", "entities": "", "has_entities": False}
    job = Job(row, "clean", "raw", "prisma-v3.0", p, {"language_code": "hi-IN"})
    cache, be = Cache(tmp_path / "c.sqlite"), Counting()
    n_chunks = len(chunks(_speechy(70)))
    assert n_chunks >= 3 and 70 > LIMIT_S
    df = run_jobs([job], mock=False, max_calls=1, backends={"prisma-v3.0": be}, cache=cache)
    assert be.n == 1 and df.empty                           # budget ran out mid-clip: no partial transcript saved
    df = run_jobs([job], mock=False, max_calls=10, backends={"prisma-v3.0": be}, cache=cache)
    assert be.n == n_chunks and df.iloc[0]["hypothesis"].startswith("part1")  # first chunk came from cache
    run_jobs([job], mock=False, max_calls=10, backends={"prisma-v3.0": be}, cache=cache)
    assert be.n == n_chunks                                 # fully cached: zero calls
