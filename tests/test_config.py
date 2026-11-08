import subprocess
import sys

from shorgul.config import load_config, seed_for
from shorgul.data.tts_generator import read_script, tts_key, tts_payload
from shorgul.asr.cache import asr_key


def test_seed_stable_across_processes():
    code = "from shorgul.config import seed_for; print(seed_for('hi_000','market_0'))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout.strip()
    assert int(out) == seed_for("hi_000", "market_0")
    assert seed_for("hi_000", "market_0") != seed_for("hi_000", "market_10")


def test_config_has_all_conditions():
    conds = load_config()["conditions"]
    assert list(conds)[:7] == ["clean", "phone", "loss_5", "traffic_10", "traffic_5", "market_10", "market_0"]
    assert "opus_voip" in conds


def test_hinglish_script():
    lines = read_script(load_config_path())
    assert len(lines) == 25
    assert all(l["entities"] for l in lines)
    assert sum("₹" in l["text"] for l in lines) >= 24


def load_config_path():
    from shorgul.config import ROOT
    return ROOT / load_config()["data"]["hinglish_script"]


def test_cache_keys_deterministic():
    assert asr_key(b"abc", "m", {"a": 1, "b": 2}) == asr_key(b"abc", "m", {"b": 2, "a": 1})
    assert asr_key(b"abc", "m", {}) != asr_key(b"abd", "m", {})
    p = tts_payload("नमस्ते", "Nalini")
    assert tts_key(p) == tts_key(dict(p))
