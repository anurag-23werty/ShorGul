from pathlib import Path

import pytest

from shorgul.asr.base import ASRResult, MockASR
from shorgul.asr.cache import Cache
from shorgul.asr.prisma import PrismaASR
from shorgul.asr.runner import Job, params_for, run_jobs

SECRET = "test-secret-key-123"


class FakeResp:
    def __init__(self, code, js=None, text=""):
        self.status_code, self._js, self.text = code, js or {}, text or str(js)

    def json(self):
        return self._js


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def post(self, url, headers=None, data=None, files=None, timeout=None):
        self.calls.append({"headers": headers, "data": data})
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", SECRET)


def test_429_backoff_then_success():
    sess = FakeSession([FakeResp(429), FakeResp(429), FakeResp(200, {"transcript": "नमस्ते"})])
    sleeps = []
    res = PrismaASR("prisma-v3.0", session=sess, sleep=sleeps.append).transcribe(b"x", {"language_code": "hi-IN"})
    assert res.status == "ok" and res.transcript == "नमस्ते"
    assert sleeps == [1, 2]
    assert sess.calls[0]["data"]["model"] == "prisma-v3.0"


def test_400_not_retried_and_key_not_logged(capsys):
    sess = FakeSession([FakeResp(400, text='{"error":"INVALID_FORMAT"}')])
    res = PrismaASR("prisma-v2.5", session=sess, sleep=lambda s: None).transcribe(b"x", {"format": "bad"})
    assert res.status == "error_400" and len(sess.calls) == 1
    assert "model" not in sess.calls[0]["data"]  # v2.5 omits model
    assert SECRET not in capsys.readouterr().out


def test_rate_limited_gives_up_and_is_not_cacheable():
    sess = FakeSession([FakeResp(429)] * 6)
    res = PrismaASR("prisma-v3.0", session=sess, sleep=lambda s: None).transcribe(b"x", {})
    assert res.status == "rate_limited" and not res.cacheable and len(sess.calls) == 6


def test_truncated_flag():
    sess = FakeSession([FakeResp(200, {"transcript": "a", "truncated": True})])
    res = PrismaASR("prisma-v3.0", session=sess, sleep=lambda s: None).transcribe(b"x", {})
    assert res.status == "ok_truncated" and res.cacheable


class CountingBackend:
    billed = True

    def __init__(self, name="prisma-v3.0"):
        self.name, self.n = name, 0

    def transcribe(self, audio, params):
        self.n += 1
        return ASRResult("hyp", "ok", 0.1)


def _jobs(tmp_path: Path, n=3):
    jobs = []
    for i in range(n):
        p = tmp_path / f"c{i}.wav"
        p.write_bytes(f"audio{i}".encode())
        row = {"clip_id": f"c{i}", "lang": "hi", "source": "fleurs", "reference": "a b c",
               "entities": "", "has_entities": False}
        jobs.append(Job(row, "phone", "raw", "prisma-v3.0", p, {"language_code": "hi-IN"}))
    return jobs


def test_cache_prevents_second_call_and_max_calls(tmp_path):
    cache, be = Cache(tmp_path / "c.sqlite"), CountingBackend()
    jobs = _jobs(tmp_path)
    df1 = run_jobs(jobs, mock=False, max_calls=2, backends={"prisma-v3.0": be}, cache=cache)
    assert be.n == 2 and len(df1) == 2          # third job held back by max-calls
    df2 = run_jobs(jobs, mock=False, max_calls=5, backends={"prisma-v3.0": be}, cache=cache)
    assert be.n == 3 and len(df2) == 3          # only the uncached one is called
    run_jobs(jobs, mock=False, max_calls=5, backends={"prisma-v3.0": be}, cache=cache)
    assert be.n == 3                            # fully cached: zero calls


def test_params_format_and_context():
    fleurs = {"lang": "hi", "has_entities": False}
    hing = {"lang": "hinglish", "has_entities": True}
    assert params_for("prisma-v3.0", fleurs, "raw")["format"] == "verbatim"
    assert params_for("prisma-v2.5", hing, "raw") == {"language_code": "en-IN", "format": "transcribe"}
    ctx = params_for("prisma-v3.0", hing, "context")
    assert ctx["language_code"] == "hi-IN,en-IN" and "topic" in ctx and ctx["keyterms"].startswith("[")
    assert params_for("whisper-small", hing, "raw")["language"] == "hi"


def test_mock_is_deterministic_and_degrades():
    m = MockASR("prisma-v2.5")
    ref = " ".join(f"w{i}" for i in range(200))
    p = {"_reference": ref, "_variant": "raw"}
    clean = m.transcribe(b"a", {**p, "_condition": "clean"}).transcript
    hard = m.transcribe(b"a", {**p, "_condition": "market_0"}).transcript
    assert clean == m.transcribe(b"a", {**p, "_condition": "clean"}).transcript
    assert sum(w in ref.split() for w in hard.split()) < sum(w in ref.split() for w in clean.split())
