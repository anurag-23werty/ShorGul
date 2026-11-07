"""Entity hit rate for call-centre lines: ₹ amounts, dates, day numbers (written-form match)."""
from __future__ import annotations

import re

from shorgul.metrics.normalize import normalize_text

MONTHS: dict[int, list[str]] = {
    1: ["जनवरी", "january", "jan"], 2: ["फरवरी", "february", "feb"], 3: ["मार्च", "march", "mar"],
    4: ["अप्रैल", "अप्रेल", "april", "apr"], 5: ["मई", "may"], 6: ["जून", "june", "jun"],
    7: ["जुलाई", "july", "jul"], 8: ["अगस्त", "august", "aug"],
    9: ["सितंबर", "सितम्बर", "september", "sept", "sep"], 10: ["अक्टूबर", "अक्तूबर", "october", "oct"],
    11: ["नवंबर", "नवम्बर", "november", "nov"], 12: ["दिसंबर", "दिसम्बर", "december", "dec"],
}
_ALIAS = {normalize_text(a): m for m, names in MONTHS.items() for a in names}


def parse_entities(spec: str) -> list[str]:
    return [e.strip() for e in (spec or "").split(";") if e.strip()]


def _month_of(tokens: list[str]) -> set[int]:
    return {_ALIAS[t] for t in tokens if t in _ALIAS}


_ORDINAL = re.compile(r"\b(\d+)(st|nd|rd|th|वीं|वां|वी)\b")


def _tokens(text: str) -> list[str]:
    return _ORDINAL.sub(r"\1", normalize_text(text)).split()


def entity_hit(entity: str, hypothesis: str) -> bool:
    ent_toks = _tokens(entity)
    hyp_toks = _tokens(hypothesis)
    nums = [t for t in ent_toks if t.isdigit()]
    if not nums or any(n not in hyp_toks for n in nums):
        return False
    months = _month_of(ent_toks)
    return not months or bool(months & _month_of(hyp_toks))


def entity_hit_rate(entities: str, hypothesis: str) -> float:
    ents = parse_entities(entities)
    if not ents:
        return float("nan")
    return sum(entity_hit(e, hypothesis) for e in ents) / len(ents)
