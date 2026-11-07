"""WER / CER on normalized text (Hinglish compared after romanization)."""
from __future__ import annotations

import jiwer

from shorgul.metrics.normalize import normalize_text, romanize


def prep(text: str, lang: str) -> str:
    return romanize(text) if lang == "hinglish" else normalize_text(text)


def wer_cer(reference: str, hypothesis: str, lang: str) -> tuple[float, float]:
    ref, hyp = prep(reference, lang), prep(hypothesis, lang)
    if not ref:
        return float("nan"), float("nan")
    if not hyp:
        return 1.0, 1.0
    return float(jiwer.wer(ref, hyp)), float(jiwer.cer(ref, hyp))
