"""Hindi number / currency / month lexicon in Devanagari and common romanized spellings."""
from __future__ import annotations

# 0-100. Devanagari canonical forms, then extra romanized spellings seen in ASR output.
# Romanized keys are ALSO auto-derived from the Devanagari via transliteration (see repair._keys).
NUMBERS: dict[int, tuple[list[str], list[str]]] = {
    0: (["शून्य", "शुन्य", "शुन्ये"], ["shunya", "shoonya", "sunya", "zero"]),
    1: (["एक"], ["ek", "one"]), 2: (["दो"], ["do", "two"]), 3: (["तीन", "थीन"], ["teen", "tin", "three"]),
    4: (["चार"], ["char", "chaar", "four"]), 5: (["पांच", "पाँच", "पाच", "पाज"], ["paanch", "panch", "five"]),
    6: (["छह", "छः", "छे", "छै"], ["chhah", "chhe", "chah", "chhey", "six"]), 7: (["सात", "साथ"], ["saat", "sat", "seven"]),
    8: (["आठ"], ["aath", "ath", "eight"]), 9: (["नौ", "नो"], ["nau", "nou", "nao", "nine"]), 10: (["दस"], ["das", "dus", "ten"]),
    11: (["ग्यारह"], ["gyarah", "gyara", "eleven"]), 12: (["बारह", "बारा"], ["barah", "bara", "baarah", "twelve"]),
    13: (["तेरह"], ["terah", "tera"]), 14: (["चौदह"], ["chaudah", "chauda", "chodah"]),
    15: (["पंद्रह", "पन्द्रह", "पंद्रा"], ["pandrah", "pandra", "fifteen"]), 16: (["सोलह"], ["solah", "sola"]),
    17: (["सत्रह"], ["satrah", "satra"]), 18: (["अठारह", "अट्ठारह"], ["atharah", "athara", "attharah"]),
    19: (["उन्नीस"], ["unnis", "unnees"]), 20: (["बीस"], ["bees", "bis", "twenty"]),
    21: (["इक्कीस"], ["ikkis", "ikkees"]), 22: (["बाईस"], ["bais", "baees", "baaees"]), 23: (["तेईस"], ["teis", "teyis"]),
    24: (["चौबीस"], ["chaubis", "chaubees"]), 25: (["पच्चीस"], ["pachchis", "pachis", "pachees", "pachchees"]),
    26: (["छब्बीस"], ["chhabbis", "chabbis"]), 27: (["सत्ताईस"], ["sattais", "sattaees"]),
    28: (["अट्ठाईस", "अठाईस"], ["atthais", "athais", "atthaees"]), 29: (["उनतीस"], ["untis", "unatees"]),
    30: (["तीस"], ["tees", "tis", "thirty"]), 31: (["इकतीस", "इकत्तीस"], ["iktis", "iktees", "ikatees"]),
    32: (["बत्तीस"], ["battis"]), 33: (["तैंतीस"], ["taintis"]), 34: (["चौंतीस"], ["chauntis"]),
    35: (["पैंतीस"], ["paintis"]), 36: (["छत्तीस"], ["chhattis", "chattis"]), 37: (["सैंतीस"], ["saintis"]),
    38: (["अड़तीस"], ["adtis", "artis"]), 39: (["उनतालीस"], ["untalis"]), 40: (["चालीस"], ["chalis", "chaalis", "chalees", "forty"]),
    41: (["इकतालीस"], ["iktalis"]), 42: (["बयालीस"], ["bayalis"]), 43: (["तैंतालीस"], ["taintalis"]),
    44: (["चवालीस", "चौवालीस"], ["chavalis", "chauvalis"]), 45: (["पैंतालीस"], ["paintalis"]),
    46: (["छियालीस"], ["chhiyalis"]), 47: (["सैंतालीस"], ["saintalis"]), 48: (["अड़तालीस"], ["adtalis", "artalis"]),
    49: (["उनचास"], ["unchas"]), 50: (["पचास"], ["pachas", "pachaas", "fifty"]), 51: (["इक्यावन"], ["ikyavan"]),
    52: (["बावन"], ["bavan", "baavan"]), 53: (["तिरेपन"], ["tirepan"]), 54: (["चौवन"], ["chauvan"]),
    55: (["पचपन"], ["pachpan"]), 56: (["छप्पन"], ["chhappan", "chappan"]), 57: (["सत्तावन"], ["sattavan"]),
    58: (["अट्ठावन"], ["atthavan"]), 59: (["उनसठ"], ["unsath"]), 60: (["साठ"], ["saath", "sixty"]),
    61: (["इकसठ"], ["iksath"]), 62: (["बासठ"], ["basath"]), 63: (["तिरसठ"], ["tirsath"]), 64: (["चौंसठ"], ["chaunsath"]),
    65: (["पैंसठ"], ["painsath"]), 66: (["छियासठ"], ["chhiyasath"]), 67: (["सड़सठ"], ["sadsath"]), 68: (["अड़सठ"], ["adsath"]),
    69: (["उनहत्तर"], ["unhattar"]), 70: (["सत्तर"], ["sattar", "seventy"]), 71: (["इकहत्तर"], ["ikhattar"]),
    72: (["बहत्तर"], ["bahattar"]), 73: (["तिहत्तर"], ["tihattar"]), 74: (["चौहत्तर"], ["chauhattar"]),
    75: (["पचहत्तर"], ["pachhattar"]), 76: (["छिहत्तर"], ["chhihattar"]), 77: (["सतहत्तर"], ["sathattar"]),
    78: (["अठहत्तर"], ["athhattar"]), 79: (["उन्यासी"], ["unyasi"]), 80: (["अस्सी"], ["assi", "eighty"]),
    81: (["इक्यासी"], ["ikyasi"]), 82: (["बयासी"], ["bayasi"]), 83: (["तिरासी"], ["tirasi"]), 84: (["चौरासी"], ["chaurasi"]),
    85: (["पचासी"], ["pachasi"]), 86: (["छियासी"], ["chhiyasi"]), 87: (["सत्तासी"], ["sattasi"]), 88: (["अट्ठासी"], ["atthasi"]),
    89: (["नवासी"], ["navasi"]), 90: (["नब्बे"], ["nabbe", "ninety"]), 91: (["इक्यानवे"], ["ikyanve"]),
    92: (["बानवे"], ["baanve", "banve"]), 93: (["तिरानवे"], ["tiranve"]), 94: (["चौरानवे"], ["chauranve"]),
    95: (["पचानवे"], ["pachanve"]), 96: (["छियानवे"], ["chhiyanve"]), 97: (["सत्तानवे"], ["sattanve"]),
    98: (["अट्ठानवे"], ["atthanve"]), 99: (["निन्यानवे"], ["ninyanve"]),
}
SCALES: dict[int, list[str]] = {
    100: ["सौ", "सो", "sau", "so", "hundred"],
    1000: ["हज़ार", "हजार", "हाजार", "हाज़ार", "हाजा", "hazaar", "hazar", "hajar", "hajaar", "thousand"],
    100_000: ["लाख", "lakh", "lac", "lakhs"],
    10_000_000: ["करोड़", "करोड", "crore", "karod", "karor", "crores"],
}
# multiplier words: value applied to the following scale ("dhai hazaar" = 2,500)
FRACTIONS: dict[str, float] = {"डेढ़": 1.5, "डेढ": 1.5, "dedh": 1.5, "derh": 1.5, "ढाई": 2.5, "dhai": 2.5, "dhaai": 2.5}
# modifiers on the following number ("saade teen sau" = 350, "paune do hazaar" = 1,750)
MODIFIERS: dict[str, float] = {"साढ़े": 0.5, "साढे": 0.5, "saade": 0.5, "sadhe": 0.5, "saadhe": 0.5,
                               "सवा": 0.25, "sava": 0.25, "sawa": 0.25, "पौने": -0.25, "paune": -0.25, "pone": -0.25}
CURRENCY = {"रुपये", "रुपए", "रुपया", "रुपे", "रपे", "रूपये", "रूपए", "रुपय", "rupay", "rupaye", "rupaiye", "rupee",
            "rupees", "rupe", "rupya", "rupaya", "rs", "inr"}
DAY_WORDS = {"तारीख", "तारीख़", "tarikh", "tareekh", "tarik", "tareek", "date"}
# romanized/English month spellings -> English canonical; Devanagari and English are kept as written
MONTHS: dict[int, list[str]] = {
    1: ["जनवरी", "january", "jan", "janavari", "janvari", "janwari"],
    2: ["फरवरी", "फ़रवरी", "फर्वरी", "february", "feb", "faravari", "farvari", "pharvari", "farwari"],
    3: ["मार्च", "march", "mar"], 4: ["अप्रैल", "अप्रेल", "april", "apr", "aprail", "aprel"],
    5: ["मई", "may", "mai", "mayi"], 6: ["जून", "जुन", "june", "jun", "joon"],
    7: ["जुलाई", "july", "jul", "julai", "julaai"], 8: ["अगस्त", "august", "aug", "agast", "agust"],
    9: ["सितंबर", "सितम्बर", "september", "sep", "sept", "sitambar", "sitamber"],
    10: ["अक्टूबर", "अक्तूबर", "october", "oct", "aktubar", "aktoobar", "october"],
    11: ["नवंबर", "नवम्बर", "november", "nov", "navambar", "navamber"],
    12: ["दिसंबर", "दिसम्बर", "december", "dec", "disambar", "disamber"],
}
ENGLISH_MONTH = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July",
                 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}
AMBIGUOUS_MONTH = {"mai", "may"}  # "mai" = में/मैं in romanized Hindi: only a month right after a day number
