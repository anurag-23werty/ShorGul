import pytest

from shorgul.entities.repair import indian_group, repair

CONVERT = [
    # --- romanized Hindi amounts (Prisma v2.5 en-IN style) ---
    ("chaar hazaar paanch sau rupay", "₹4,500"),
    ("barah hazaar teen sau rupee", "₹12,300"),
    ("saat sau pachas rupay", "₹750"),
    ("do hazaar rupay ka payment", "₹2,000 ka payment"),
    ("pandrah hazaar rupaye", "₹15,000"),
    ("ek lakh rupaye", "₹1,00,000"),
    ("das lakh pachas hazaar rupaye", "₹10,50,000"),
    ("do crore rupaye", "₹2,00,00,000"),
    ("teen sau ninyanve rupay", "₹399"),
    ("nau sau ninyanve rupees", "₹999"),
    # --- fractions and modifiers ---
    ("dedh hazaar rupaye", "₹1,500"),
    ("dhai hazaar rupay", "₹2,500"),
    ("saade teen sau rupaye", "₹350"),
    ("paune do hazaar rupay", "₹1,750"),
    ("sava lakh rupaye", "₹1,25,000"),
    ("dhai lakh", "2,50,000"),
    # --- Devanagari amounts (Whisper / verbatim style) ---
    ("चालीस हज़ार रुपये", "₹40,000"),
    ("चार हजार पांच सौ रुपये", "₹4,500"),
    ("साथ सो पचास रपे", "₹750"),
    ("पंद्रह हाजार रुपे", "₹15,000"),
    ("एक लाख रुपये", "₹1,00,000"),
    ("ऐसो दो हजार रुपये", "ऐसो ₹2,000"),                         # a word merely ending in सो doesn't block
    ("दो सौ पचास रुपए", "₹250"),
    # --- currency normalization of digits ---
    ("4,500 रुपये की", "₹4,500 की"),
    ("250 rupees", "₹250"),
    ("₹3,999 का", "₹3,999 का"),
    ("2 हाजा रुपे", "₹2,000"),
    ("15 hazaar rupay", "₹15,000"),
    # --- dates ---
    ("paanch march ko", "5 March ko"),
    ("dus april tak", "10 April tak"),
    ("pandrah june tak", "15 June tak"),
    ("maine do faravari ko", "maine 2 February ko"),
    ("do shunya janavari ko", "20 January ko"),
    ("एक जुलाई को", "1 जुलाई को"),
    ("1 8 अगस्त को", "18 अगस्त को"),
    ("2 0 जनवरी को", "20 जनवरी को"),
    ("3 1 मई को", "31 मई को"),
    ("3/1/May को", "31 May को"),
    ("pachchis tarikh ko", "25 tarikh ko"),
    ("पंद्रह तारीख", "15 तारीख"),
    ("unnis mai ko", "19 May ko"),
    ("इकतीस दिसंबर", "31 दिसंबर"),
    # --- full sentences ---
    ("namaste sir aapki loan emi chaar hazaar paanch sau rupay ki paanch march ko due hai",
     "namaste sir aapki loan emi ₹4,500 ki 5 March ko due hai"),
    ("मेरे अकाउंट से ₹3,999 का ट्रांज़ैक्शन 1 8 अगस्त को हुआ है, प्लीज चेक कीजिये।",
     "मेरे अकाउंट से ₹3,999 का ट्रांज़ैक्शन 18 अगस्त को हुआ है, प्लीज चेक कीजिये।"),
]

KEEP = [  # ambiguous or non-entity: must NOT be converted
    "xyzz sau ninyanave rupay",    # unparseable head: never convert just the tail into a wrong amount (₹99)
    "नोसो निन्यानवे रुपे",            # Whisper's merged "नौसौ": same rule
    "do teen log aaye the",
    "kar do",
    "please kar do na",
    "ek baar phir se try kijiye",
    "main ek minute mein aata hoon",
    "do din baad",
    "teen chaar baar call kiya",
    "mai kal aaunga",
    "आप दो मिनट रुकिए",
    "एक काम कीजिए",
    "so what is the status",
    "das minute",
    "2 0 को",                      # split digits with no month: leave
    "the date was 1 August",       # information truly lost: nothing to repair
    "",
]


@pytest.mark.parametrize("src,want", CONVERT)
def test_converts(src, want):
    assert repair(src) == want


@pytest.mark.parametrize("src", KEEP)
def test_keeps_non_entities(src):
    assert repair(src) == src


def test_idempotent():
    for src, _ in CONVERT:
        once = repair(src)
        assert repair(once) == once


def test_indian_grouping():
    assert [indian_group(n) for n in (5, 999, 1000, 12300, 100000, 1050000, 20000000)] == \
        ["5", "999", "1,000", "12,300", "1,00,000", "10,50,000", "2,00,00,000"]


def test_case_count():
    assert len(CONVERT) + len(KEEP) >= 40
