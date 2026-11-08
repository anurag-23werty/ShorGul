import numpy as np
from scipy.signal import welch

from shorgul.degrade.pipeline import degrade_audio
from shorgul.degrade.telephony import phone_channel


def _wideband(n=16000 * 3):
    return (0.1 * np.random.default_rng(0).standard_normal(n)).astype(np.float32)


def test_phone_channel_bandlimits_and_keeps_length():
    x = _wideband()
    y = phone_channel(x)
    assert len(y) == len(x)
    f, p = welch(y, fs=16000, nperseg=1024)
    in_band = p[(f > 500) & (f < 3000)].mean()
    above = p[f > 4500].mean()
    below = p[f < 100].mean()
    assert 10 * np.log10(in_band / above) > 30
    assert 10 * np.log10(in_band / below) > 10


def test_conditions_deterministic_and_length():
    x = _wideband()
    noises = {"traffic": _wideband(16000 * 20), "market": _wideband(16000 * 20)}
    for cond in ["clean", "phone", "loss_5", "traffic_5", "market_0"]:
        a, _ = degrade_audio(x, "clip", cond, noises)
        b, _ = degrade_audio(x, "clip", cond, noises)
        assert len(a) == len(x)
        assert np.array_equal(a, b), cond
    a, _ = degrade_audio(x, "clip", "clean", noises)
    assert np.array_equal(a, x)


def test_opus_voip_keeps_length_is_deterministic_and_lossy():
    x = _wideband()
    a, _ = degrade_audio(x, "clip", "opus_voip", {})
    b, _ = degrade_audio(x, "clip", "opus_voip", {})
    assert len(a) == len(x) and np.array_equal(a, b)
    f, p = welch(a, fs=16000, nperseg=1024)
    assert p[f > 5000].mean() < p[(f > 300) & (f < 3000)].mean() / 100  # 8 kbps Opus drops to narrowband


import pytest  # noqa: E402

from shorgul.degrade import amr  # noqa: E402


@pytest.mark.skipif(not amr.available(), reason="libopencore-amrnb not installed")
def test_amrnb_mobile_is_real_lossy_narrowband_and_deterministic():
    x = _wideband()
    a, _ = degrade_audio(x, "clip", "amrnb_mobile", {})
    b, _ = degrade_audio(x, "clip", "amrnb_mobile", {})
    assert len(a) == len(x) and np.array_equal(a, b)
    f, p = welch(a, fs=16000, nperseg=1024)
    assert p[f > 4500].mean() < p[(f > 300) & (f < 3000)].mean() / 100
    t = np.arange(8000) / 8000
    tone = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    y = amr.amrnb_roundtrip(tone)
    assert len(y) == len(tone) and 0.05 < np.abs(y).max() < 1.0   # a real codec: changed, but not silence
    assert not np.allclose(y, tone, atol=1e-3)
