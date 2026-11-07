"""Text normalization for fair WER/CER across Hindi, Bengali, Tamil and Hinglish."""
from __future__ import annotations

import re
import unicodedata

from indic_transliteration import sanscript

_NATIVE_DIGITS = str.maketrans("०१२३४५६७८९০১২৩৪৫৬৭৮৯௦௧௨௩௪௫௬௭௮௯",
                               "0123456789" * 3)
_DIGIT_COMMA = re.compile(r"(?<=\d)[,٬](?=\d)")
_DEVA_WORD = re.compile(r"[ऀ-ॿ]+")


def _keep(ch: str) -> bool:
    cat = unicodedata.category(ch)
    return not (cat.startswith("P") or cat.startswith("S"))


def normalize_text(s: str) -> str:
    """NFC, native digits -> ASCII, 4,500 -> 4500, drop punctuation/symbols (incl. danda, ₹), lowercase."""
    s = unicodedata.normalize("NFC", s or "").translate(_NATIVE_DIGITS)
    s = _DIGIT_COMMA.sub("", s)
    s = "".join(ch if _keep(ch) else " " for ch in s)
    # Spelling variants, not recognition errors:
    #  - Devanagari nukta dropped: "फ़रवरी" == "फरवरी" (U+093C). Not for Bengali, where য়/ড়/ঢ়
    #    are distinct letters.
    #  - chandrabindu -> anusvara: "एजेंसियाँ" == "एजेंसियां" (U+0901 -> U+0902, U+0981 -> U+0982)
    s = unicodedata.normalize("NFD", s)
    s = s.replace("़", "").replace("ँ", "ं").replace("ঁ", "ং")
    s = unicodedata.normalize("NFC", s)
    return " ".join(s.lower().split())


def _romanize_word(w: str) -> str:
    r = sanscript.transliterate(w, sanscript.DEVANAGARI, sanscript.ITRANS).lower()
    last = w[-1]
    if "क" <= last <= "ह" and r.endswith("a"):  # schwa deletion: "लोन" -> "lon", not "lona"
        r = r[:-1]
    return r


def romanize(s: str) -> str:
    """Hinglish: put Devanagari and Latin on one (Latin) footing so script choice is not an 'error'."""
    s = _DEVA_WORD.sub(lambda m: _romanize_word(m.group()), normalize_text(s))
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return " ".join(s.split())
