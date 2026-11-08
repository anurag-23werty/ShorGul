import numpy as np
import pandas as pd
import pytest

from shorgul.asr.runner import applies, params_for
from shorgul.audio import write_wav
from shorgul.config import is_hinglish
from shorgul.metrics.aggregate import score_rows


def test_is_hinglish():
    assert is_hinglish("hinglish") and is_hinglish("hinglish_human") and is_hinglish("hinglish_heldout")
    assert not is_hinglish("hi")


def test_heldout_script_is_separate_and_valid():
    from shorgul.config import ROOT, load_config
    from shorgul.data.tts_generator import read_script
    cfg = load_config()["data"]
    held = read_script(ROOT / cfg["heldout_script"])
    dev = read_script(ROOT / cfg["hinglish_script"])
    assert len(held) == 25 and all(l["entities"] for l in held)
    assert not {l["clip_id"] for l in held} & {l["clip_id"] for l in dev}
    assert not set(cfg["heldout_voices"]) & set(cfg["tts_voices"])


def test_human_gets_hinglish_behaviour_but_own_label():
    row = {"lang": "hinglish_human", "has_entities": True}
    assert params_for("prisma-v3.0", row, "raw")["language_code"] == "hi-IN,en-IN"
    assert params_for("prisma-v2.5", row, "matched") == {"language_code": "hi-IN", "format": "transcribe"}
    assert applies("prisma-v3.0", "context", "clean", row)
    df = pd.DataFrame([{"clip_id": "hu_000", "lang": "hinglish_human", "source": "human", "condition": "clean",
                        "variant": "raw", "model": "prisma-v3.0", "reference": "आपकी EMI ₹4,500 की 5 मार्च",
                        "hypothesis": "आपकी EMI 4,500 रुपये की 5 March", "entities": "₹4,500;5 मार्च",
                        "latency_s": 0.2, "status": "ok", "cache_key": "k"}])
    s = score_rows(df).iloc[0]
    assert s["entity_hit_rate"] == 1.0 and s["wer_cn"] < s["wer"]  # currency-neutral applies to human set too


def test_load_human(tmp_path, monkeypatch):
    import shorgul.data.human as human
    monkeypatch.setattr(human, "ROOT", tmp_path)
    hd = tmp_path / "human"
    write_wav(hd / "a.wav", np.zeros(16000 * 3, dtype=np.float32))
    pd.DataFrame([{"file": "a.wav", "reference": "₹4,500 की 5 मार्च", "entities": "₹4,500;5 मार्च"}]).to_csv(hd / "refs.csv", index=False)
    rows = human.load_human(hd, tmp_path / "clean")
    assert rows[0]["clip_id"] == "hu_000" and rows[0]["lang"] == "hinglish_human" and rows[0]["source"] == "human"
    write_wav(hd / "long.wav", np.zeros(16000 * 31, dtype=np.float32))
    pd.DataFrame([{"file": "long.wav", "reference": "x"}]).to_csv(hd / "refs.csv", index=False)
    with pytest.raises(ValueError, match="30"):
        human.load_human(hd, tmp_path / "clean")
