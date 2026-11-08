"""Entity repair: a model-agnostic post-processor for Hindi/Hinglish ASR output.

Turns spoken-form amounts and dates into written form a CRM can use:
    "chaar hazaar paanch sau rupay"  -> "₹4,500"
    "चालीस हज़ार रुपये"                -> "₹40,000"
    "4,500 रुपये"                     -> "₹4,500"
    "pandrah june" / "1 8 अगस्त"      -> "15 June" / "18 अगस्त"
    "3/1/May"                        -> "31 May"

Anchoring rule (precision first): number words are converted ONLY in an entity context:
the phrase is followed by a currency word, a month or तारीख/tarikh, is preceded by ₹, or contains
a scale word (sau/hazaar/lakh/crore). So "do teen log" and "kar do" are left alone.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from shorgul.entities.lexicon import (AMBIGUOUS_MONTH, CURRENCY, DAY_WORDS, ENGLISH_MONTH, FRACTIONS,
                                      MODIFIERS, MONTHS, NUMBERS, SCALES)

_PUNCT = ",.।?!;:\"'()[]{}"
_DEVA = re.compile(r"[ऀ-ॿ]")


def _key(word: str) -> str:
    """Matching key: Devanagari -> nukta/chandrabindu-free NFC; Latin -> lowercase spelling squash."""
    w = unicodedata.normalize("NFC", word.strip(_PUNCT))
    if _DEVA.search(w):
        w = unicodedata.normalize("NFD", w).replace("़", "").replace("ँ", "ं")
        return unicodedata.normalize("NFC", w)
    w = w.lower().replace("ee", "i").replace("oo", "u").replace("aa", "a").replace("w", "v")
    return re.sub(r"(.)\1+", r"\1", w)  # collapse repeated letters


@lru_cache(maxsize=1)
def _tables() -> dict[str, dict]:
    from shorgul.metrics.normalize import romanize
    units: dict[str, int] = {}
    auto: dict[str, int] = {}
    for n, (deva, roman) in NUMBERS.items():
        for w in deva + roman:
            units[_key(w)] = n
        for w in deva:  # auto-derive a romanized spelling from each Devanagari form
            auto.setdefault(_key(romanize(w)), n)
    for k, n in auto.items():
        units.setdefault(k, n)  # explicit spellings win on collision
    months = {_key(w): m for m, ws in MONTHS.items() for w in ws}
    scales = {_key(w): v for v, ws in SCALES.items() for w in ws}
    for k in list(scales):
        units.pop(k, None)  # "so"/"सो" = hundred, never a unit
    return {"units": units, "scales": scales, "months": months,
            "fracs": {_key(w): v for w, v in FRACTIONS.items()},
            "mods": {_key(w): v for w, v in MODIFIERS.items()},
            "currency": {_key(w) for w in CURRENCY}, "days": {_key(w) for w in DAY_WORDS}}


@dataclass
class Tok:
    raw: str
    core: str        # without surrounding punctuation and without a leading ₹
    rupee: bool      # raw started with ₹
    tail: str        # trailing punctuation to re-attach

    @classmethod
    def of(cls, raw: str) -> "Tok":
        rupee = raw.startswith("₹")
        body = raw[1:] if rupee else raw
        core = body.rstrip(_PUNCT)
        tail = body[len(core):]
        return cls(raw, core.lstrip(_PUNCT), rupee, tail)


def _digits(core: str) -> int | None:
    s = core.replace(",", "")
    return int(s) if s.isdigit() else None


def indian_group(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    return ",".join(([head] if head else []) + parts + [tail])


@dataclass
class Phrase:
    value: float
    end: int              # exclusive token index
    has_scale: bool
    digit_seq: list[int]  # set when the phrase is 2 single-digit units read digit by digit ("do shunya")


def _parse(toks: list[Tok], i: int) -> Phrase | None:
    t = _tables()
    total, cur, mod, frac = 0.0, 0.0, 0.0, None
    last_num, has_scale, singles, j = False, False, [], i
    while j < len(toks):
        k = _key(toks[j].core)
        d = _digits(toks[j].core)
        if j > i and toks[j].rupee:
            break
        if d is not None or k in t["units"]:
            n = d if d is not None else t["units"][k]
            if last_num:
                # digit-by-digit reading of a day: "do shunya" / "1 8" (resolved by the caller)
                if singles and len(singles) == 1 and singles[0] < 10 and n < 10 and not has_scale:
                    singles.append(n)
                    j += 1
                    break
                break
            cur += n + mod
            mod = 0.0
            singles = [n] if (n < 10 and cur == n) else []
            last_num = True
        elif k in t["scales"]:
            if cur == 0 and total == 0 and frac is None and mod == 0:
                break  # a bare scale word ("so what…", "hundred") is not a number
            s = t["scales"][k]
            if frac is not None:
                base = frac
            elif cur == 0:
                base = 1.0 + mod  # "sava lakh" = 1.25 lakh
            else:
                base = cur
            mod = 0.0
            if s == 100:
                cur = base * 100
            else:
                total += base * s
                cur = 0.0
            frac, has_scale, last_num, singles = None, True, False, []
        elif k in t["fracs"] and j + 1 < len(toks) and _key(toks[j + 1].core) in t["scales"]:
            frac = t["fracs"][k]
            last_num = False
        elif k in t["mods"] and j + 1 < len(toks):
            mod = t["mods"][k]
            last_num = False
        else:
            break
        if toks[j].tail and toks[j].tail.strip(","):  # sentence punctuation ends a phrase
            j += 1
            break
        j += 1
    if j == i or (total == 0 and cur == 0 and not singles):
        return None
    return Phrase(total + cur, j, has_scale, singles if len(singles) == 2 else [])


def _ends_in_scale(core: str) -> bool:
    """Previous token is, or ends in, a scale word ("sau", "नोसो" = नौ+सौ merged by the ASR)."""
    k = _key(core)
    if not k:
        return False
    t = _tables()
    return k in t["scales"] or any(k.endswith(sc) and k[: -len(sc)] in t["units"] for sc in t["scales"]
                                   if len(sc) >= 2 and _DEVA.search(sc))  # merged unit+scale, e.g. नो+सो


def _month_of(tok: Tok, after_number: bool) -> int | None:
    k = _key(tok.core)
    m = _tables()["months"].get(k)
    if m and tok.core.lower() in AMBIGUOUS_MONTH and not after_number:
        return None
    return m


def _month_text(tok: Tok, m: int) -> str:
    if _DEVA.search(tok.core):
        return tok.core
    return ENGLISH_MONTH[m]


def repair(text: str) -> str:
    """Rewrite spoken-form ₹ amounts and dates into written form; leave everything else as is."""
    if not text:
        return text
    t = _tables()
    toks = [Tok.of(w) for w in text.split()]
    out: list[str] = []
    i = 0
    while i < len(toks):
        tok = toks[i]
        ph = _parse(toks, i)
        prev_scale = i > 0 and _ends_in_scale(toks[i - 1].core)
        if ph is not None and prev_scale:
            # the number started earlier but its head didn't parse ("xyz sau ninyanave"): converting only the
            # tail would invent a wrong amount, so leave the whole thing as spoken
            ph = None
        if ph is None:
            out.append(tok.raw)
            i += 1
            continue
        nxt = toks[ph.end] if ph.end < len(toks) else None
        nk = _key(nxt.core) if nxt else ""
        last_tail = toks[ph.end - 1].tail
        month = _month_of(nxt, True) if nxt else None
        value = ph.value
        if ph.digit_seq:
            joined = ph.digit_seq[0] * 10 + ph.digit_seq[1]
            if month and 1 <= joined <= 31:
                out.append(f"{joined} {_month_text(nxt, month)}{nxt.tail}")
                i = ph.end + 1
                continue
            # not a date: keep the first number only and continue from the second token
            ph = _parse(toks[: i + 1], i) or ph
            value, ph.end = (ph.digit_seq[0] if ph.digit_seq else value), i + 1
            nxt = toks[ph.end] if ph.end < len(toks) else None
            nk = _key(nxt.core) if nxt else ""
            month = _month_of(nxt, True) if nxt else None
            last_tail = toks[ph.end - 1].tail
        if value != int(value) or value <= 0 and not tok.rupee:
            out.append(tok.raw)
            i += 1
            continue
        n = int(value)
        all_digits = all(_digits(x.core) is not None for x in toks[i:ph.end])
        if nk in t["currency"] and not (last_tail and last_tail.strip(",")):
            out.append(f"₹{indian_group(n)}{nxt.tail}")
            i = ph.end + 1
        elif tok.rupee:
            out.append(f"₹{indian_group(n)}{last_tail}")
            i = ph.end
        elif month and 1 <= n <= 31 and not (last_tail and last_tail.strip(",")):
            out.append(f"{n} {_month_text(nxt, month)}{nxt.tail}")
            i = ph.end + 1
        elif nk in t["days"] and 1 <= n <= 31:
            out.append(f"{n}{last_tail}")
            i = ph.end
        elif ph.has_scale and not all_digits:
            out.append(f"{indian_group(n)}{last_tail}")
            i = ph.end
        else:  # unanchored: leave the words exactly as they were
            out.append(tok.raw)
            i += 1
    text = " ".join(out)
    # "3/1/May" -> "31 May": a day split by slashes right before a month word
    months_alt = "|".join(sorted({re.escape(w) for ws in MONTHS.values() for w in ws}, key=len, reverse=True))
    text = re.sub(rf"(?<![\d/])(\d)/(\d)/\s*({months_alt})\b",
                  lambda m: (f"{m.group(1)}{m.group(2)} {m.group(3)}" if 1 <= int(m.group(1) + m.group(2)) <= 31
                             else m.group(0)), text, flags=re.I)
    return text
