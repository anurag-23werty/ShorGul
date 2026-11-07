import numpy as np

from shorgul.degrade.noise import active_power, mix_at_snr
from shorgul.degrade.packet_loss import apply_packet_loss


def _speech_like(n=16000 * 6, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / 16000
    env = (np.sin(2 * np.pi * 2 * t) > 0).astype(np.float32)  # on/off "syllables"
    x = 0.3 * np.sin(2 * np.pi * 220 * t) * env + 0.01 * rng.standard_normal(n)
    x[: 16000] = 0.0  # leading silence, like FLEURS
    return x.astype(np.float32)


def test_mix_hits_target_snr():
    speech = _speech_like()
    noise = np.random.default_rng(1).standard_normal(16000 * 10).astype(np.float32) * 0.1
    for snr in (10, 5, 0):
        mix = mix_at_snr(speech, noise, snr, np.random.default_rng(2))
        gain = np.dot(mix, speech) / np.dot(speech, speech)  # undo any anti-clip scaling
        n_part = mix / gain - speech
        measured = 10 * np.log10(active_power(speech) / np.mean(n_part**2))
        assert abs(measured - snr) < 0.2, (snr, measured)


def test_mix_never_clips_and_keeps_length():
    speech = _speech_like() * 3
    noise = np.random.default_rng(1).standard_normal(16000 * 2).astype(np.float32)  # shorter -> loops
    mix = mix_at_snr(speech, noise, 0, np.random.default_rng(3))
    assert len(mix) == len(speech)
    assert np.abs(mix).max() <= 0.99 + 1e-6


def test_mix_deterministic():
    speech, noise = _speech_like(), np.random.default_rng(1).standard_normal(16000 * 10).astype(np.float32)
    a = mix_at_snr(speech, noise, 5, np.random.default_rng(42))
    b = mix_at_snr(speech, noise, 5, np.random.default_rng(42))
    assert np.array_equal(a, b)


def test_packet_loss_rate():
    x = np.ones(16000 * 60, dtype=np.float32)
    out, frac = apply_packet_loss(x, 0.05, np.random.default_rng(0))
    assert 0.035 < frac < 0.065
    assert abs((out == 0).mean() - frac) < 0.01
