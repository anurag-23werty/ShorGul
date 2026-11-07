import math

from shorgul.metrics.entities import entity_hit, entity_hit_rate
from shorgul.metrics.normalize import normalize_text, romanize
from shorgul.metrics.wer_cer import wer_cer


def test_normalize_punct_digits_danda():
    assert normalize_text("नमस्ते, आप कैसे हैं?") == "नमस्ते आप कैसे हैं"
    assert normalize_text("₹4,500 की ५ मार्च।") == "4500 की 5 मार्च"
    assert normalize_text("₹1,00,000") == "100000"
    assert normalize_text("Hello  WORLD!") == "hello world"
    assert normalize_text("ফ্রেব্রুয়ারি।") == "ফ্রেব্রুয়ারি"
    assert normalize_text("फ़रवरी") == normalize_text("फरवरी")


def test_romanize_hinglish_mixed_script():
    # one Latin footing for both scripts; schwa deletion keeps it close to how Hinglish is typed
    assert romanize("नमस्ते सर") == "namaste sar"
    assert romanize("मार्च") == romanize("March") == "march"
    assert romanize("आपकी EMI, ₹4,500") == "apaki emi 4500"


def test_wer_cer_known_pairs():
    assert wer_cer("a b c d", "a b c d", "hi") == (0.0, 0.0)
    w, c = wer_cer("a b c d", "a x c", "hi")
    assert w == 0.5 and 0 < c < 1
    assert wer_cer("a b", "", "hi") == (1.0, 1.0)
    assert math.isnan(wer_cer("", "x", "hi")[0])
    assert wer_cer("नमस्ते, सर।", "नमस्ते सर", "hi")[0] == 0.0


def test_entities():
    assert entity_hit("₹4,500", "आपकी EMI ₹4500 की है")
    assert entity_hit("₹4,500", "your emi is rs. 4,500")
    assert not entity_hit("₹4,500", "चार हजार पांच सौ")       # spoken form != written form
    assert entity_hit("5 मार्च", "5th March को due है")
    assert entity_hit("5 मार्च", "५ मार्च")
    assert not entity_hit("5 मार्च", "5 अप्रैल")
    assert entity_hit("25", "25 तारीख को")
    assert entity_hit_rate("₹4,500;5 मार्च", "₹4,500 की 6 मार्च") == 0.5
    assert math.isnan(entity_hit_rate("", "x"))
