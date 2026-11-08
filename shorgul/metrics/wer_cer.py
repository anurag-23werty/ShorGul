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


# Words that only encode the currency *convention* ("₹4,500" vs "4,500 रुपये"), in romanized form.
CURRENCY_WORDS = {"rupaye", "rupae", "rupaya", "rupaiye", "rupee", "rupees", "rupay", "rs"}


def error_counts(reference: str, hypothesis: str, lang: str, currency_neutral: bool = False
                 ) -> tuple[int, int, int, int]:
    """Exact (word_errors, ref_words, char_errors, ref_chars) on normalized text.

    currency_neutral drops currency words from both sides (Hinglish only), so "₹4,500" and
    "4,500 रुपये" score the same.
    """
    ref, hyp = prep(reference, lang), prep(hypothesis, lang)
    if currency_neutral:
        ref = " ".join(w for w in ref.split() if w not in CURRENCY_WORDS)
        hyp = " ".join(w for w in hyp.split() if w not in CURRENCY_WORDS)
    n_w, n_c = len(ref.split()), len(ref)
    if not ref:
        return 0, 0, 0, 0
    if not hyp:
        return n_w, n_w, n_c, n_c
    w = jiwer.process_words(ref, hyp)
    c = jiwer.process_characters(ref, hyp)
    return (w.substitutions + w.deletions + w.insertions, n_w,
            c.substitutions + c.deletions + c.insertions, n_c)
