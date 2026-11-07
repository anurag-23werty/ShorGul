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
