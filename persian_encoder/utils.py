from __future__ import annotations

import re
from pathlib import Path

ZWNJ = "\u200c"

# Persian letters + common Arabic variants used in Persian text (without digits/punctuation)
RAW_PERSIAN_LETTER_CLASS = "اآبپتثجچحخدذرزژسشصضطظعغفقکگلمنوهیءيىكۀةؤئإأٱ"
NORMALIZED_PERSIAN_LETTER_CLASS = "اآبپتثجچحخدذرزژسشصضطظعغفقکگلمنوهیء"
PERSIAN_DIACRITIC_CLASS = "\u064b-\u065f\u0670\u06d6-\u06ed"

PERSIAN_WORD_RE = re.compile(
    rf"^[{RAW_PERSIAN_LETTER_CLASS}{PERSIAN_DIACRITIC_CLASS}]+"
    rf"(?:{ZWNJ}[{RAW_PERSIAN_LETTER_CLASS}{PERSIAN_DIACRITIC_CLASS}]+)*$"
)
NORMALIZED_PERSIAN_WORD_RE = re.compile(
    rf"^[{NORMALIZED_PERSIAN_LETTER_CLASS}]+(?:{ZWNJ}[{NORMALIZED_PERSIAN_LETTER_CLASS}]+)*$"
)
ENCODE_SOURCE_TOKEN_RE = re.compile(
    rf"[{RAW_PERSIAN_LETTER_CLASS}{PERSIAN_DIACRITIC_CLASS}{ZWNJ}]+"
    rf"|[^{RAW_PERSIAN_LETTER_CLASS}{PERSIAN_DIACRITIC_CLASS}{ZWNJ}]+"
)
DIACRITICS_RE = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
MULTI_ZWNJ_RE = re.compile(rf"{ZWNJ}+")

NORMALIZATION_TABLE = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ی",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
        "ـ": "",
    }
)

NON_PERSIAN_NORMALIZATION_TABLE = str.maketrans(
    {
        # Persian and Arabic-Indic digits -> ASCII digits
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
        # Common Persian punctuation -> ASCII
        "،": ",",
        "؛": ";",
        "؟": "?",
        "٪": "%",
        "٫": ".",
        "٬": ",",
    }
)

DEFAULT_DB_PATH = Path.home() / ".persian_encoder" / "lexicon.db"
KNOWN_MARKER = "~"
KNOWN_SPACE_MARKER = "^"
KNOWN_CODE_PREFIX = "s"
UNKNOWN_CODE_PREFIX = "u"
UNKNOWN_ASCII_CODE_PREFIX = "U"
UNKNOWN_ASCII_END = ";"
UNICODE_ESCAPE_PREFIX = "X"
UNICODE_ESCAPE_END = ";"
CODE_CHARS = set("0123456789abcdefghijklmnopqrstuvwxyz")
MAX_LOOKUP_CANDIDATES = 32
SUBWORD_ASCII_MARKER = "Y"
SUBWORD_ASCII_ESCAPE = "_"
SUBWORD_ASCII_END = ";"
LINE_ESCAPE_MARKER = "%"
LINE_ESCAPE_NEWLINE = "n"
LINE_ESCAPE_PERCENT = "p"

PERSIAN_FRAGMENT_CHARS = [
    "ا",
    "آ",
    "ب",
    "پ",
    "ت",
    "ث",
    "ج",
    "چ",
    "ح",
    "خ",
    "د",
    "ذ",
    "ر",
    "ز",
    "ژ",
    "س",
    "ش",
    "ص",
    "ض",
    "ط",
    "ظ",
    "ع",
    "غ",
    "ف",
    "ق",
    "ک",
    "گ",
    "ل",
    "م",
    "ن",
    "و",
    "ه",
    "ی",
    "ء",
    ZWNJ,
]
ASCII_FRAGMENT_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
FORCED_ASCII_FRAGMENT_MAP = {
    # Keep this human-friendly, e.g. "دانشگاهی" -> "...y"
    "ی": "y",
}

COLLOQUIAL_EXACT_MAP = {
    # آمدن
    "امد": "آمد",
    "امدم": "آمدم",
    "امدی": "آمدی",
    "امدیم": "آمدیم",
    "امدید": "آمدید",
    "امدند": "آمدند",
    "امده": "آمده",
    "امدن": "آمدن",
    "اومد": "آمد",
    "اومدم": "آمدم",
    "اومدی": "آمدی",
    "اومدیم": "آمدیم",
    "اومدید": "آمدید",
    "اومدند": "آمدند",
    "اومده": "آمده",
    "اومدن": "آمدند",
    # شدن
    "میشه": "میشود",
    "نمیشه": "نمیشود",
    "میشد": "میشد",
    "نمیشد": "نمیشد",
    # خواستن
    "میخوام": "میخواهم",
    "میخوای": "میخواهی",
    "میخواد": "میخواهد",
    "میخوایم": "میخواهیم",
    "میخواین": "میخواهید",
    "میخوان": "میخواهند",
    "نمیخوام": "نمیخواهم",
    "نمیخوای": "نمیخواهی",
    "نمیخواد": "نمیخواهد",
    "نمیخوایم": "نمیخواهیم",
    "نمیخواین": "نمیخواهید",
    "نمیخوان": "نمیخواهند",
    # دانستن
    "میدونم": "میدانم",
    "میدونی": "میدانی",
    "میدونه": "میداند",
    "میدونیم": "میدانیم",
    "میدونید": "میدانید",
    "میدونن": "میدانند",
    "نمیدونم": "نمیدانم",
    "نمیدونی": "نمیدانی",
    "نمیدونه": "نمیداند",
    "نمیدونیم": "نمیدانیم",
    "نمیدونید": "نمیدانید",
    "نمیدونن": "نمیدانند",
    # توانستن
    "میتونم": "میتوانم",
    "میتونی": "میتوانی",
    "میتونه": "میتواند",
    "میتونیم": "میتوانیم",
    "میتونید": "میتوانید",
    "میتونن": "میتوانند",
    "نمیتونم": "نمیتوانم",
    "نمیتونی": "نمیتوانی",
    "نمیتونه": "نمیتواند",
    "نمیتونیم": "نمیتوانیم",
    "نمیتونید": "نمیتوانید",
    "نمیتونن": "نمیتوانند",
    # چند معادل محاوره‌ای رایج
    "رو": "را",
    "یه": "یک",
    "دیگه": "دیگر",
    "داره": "دارد",
    "دارن": "دارند",
    "نداره": "ندارد",
    "میکنه": "میکند",
    "می‌کنه": "می‌کند",
    "میکنن": "میکنند",
    "می‌کنن": "می‌کنند",
    "کنه": "کند",
    "شه": "شود",
    "بخاطر": "به‌خاطر",
    "خیابون": "خیابان",
    "اتیش": "آتش",
    "خونه": "خانه",
    "خونم": "خانه",
    "اون": "آن",
    "اینو": "این",
    "اونو": "آن",
}


def _build_fragment_maps() -> tuple[dict[str, str], dict[str, str]]:
    if len(PERSIAN_FRAGMENT_CHARS) > len(ASCII_FRAGMENT_ALPHABET):
        raise ValueError("Not enough ASCII chars for Persian fragment map")

    used = set(FORCED_ASCII_FRAGMENT_MAP.values())
    available = [ch for ch in ASCII_FRAGMENT_ALPHABET if ch not in used]
    encode_map: dict[str, str] = {}

    for ch in PERSIAN_FRAGMENT_CHARS:
        forced = FORCED_ASCII_FRAGMENT_MAP.get(ch)
        if forced:
            encode_map[ch] = forced
            continue
        if not available:
            raise ValueError("ASCII fragment alphabet exhausted")
        encode_map[ch] = available.pop(0)

    decode_map = {v: k for k, v in encode_map.items()}
    return encode_map, decode_map


PERSIAN_FRAGMENT_ENCODE_MAP, PERSIAN_FRAGMENT_DECODE_MAP = _build_fragment_maps()


def normalize_word(word: str) -> str:
    normalized = word.strip().translate(NORMALIZATION_TABLE)
    normalized = DIACRITICS_RE.sub("", normalized)
    normalized = MULTI_ZWNJ_RE.sub(ZWNJ, normalized)
    return normalized


def normalize_non_persian_chunk(chunk: str) -> str:
    return chunk.translate(NON_PERSIAN_NORMALIZATION_TABLE)


def encode_ascii_fragment(fragment: str) -> str | None:
    normalized = normalize_word(fragment)
    if not normalized:
        return ""

    out: list[str] = []
    for ch in normalized:
        mapped = PERSIAN_FRAGMENT_ENCODE_MAP.get(ch)
        if mapped is None:
            return None
        out.append(mapped)
    return "".join(out)


def decode_ascii_fragment(payload: str) -> str | None:
    if not payload:
        return ""

    out: list[str] = []
    for ch in payload:
        mapped = PERSIAN_FRAGMENT_DECODE_MAP.get(ch)
        if mapped is None:
            return None
        out.append(mapped)
    return "".join(out)


def encode_unknown_ascii_word(word: str) -> str | None:
    return encode_ascii_fragment(word)


def decode_unknown_ascii_word(payload: str) -> str | None:
    return decode_ascii_fragment(payload)


def escape_non_ascii_text(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if ord(ch) < 128 and ch != "\"":
            out.append(ch)
            continue
        out.append(f"{KNOWN_MARKER}{UNICODE_ESCAPE_PREFIX}{ord(ch):x}{UNICODE_ESCAPE_END}")
    return "".join(out)


def decode_unicode_escape_payload(payload: str) -> str | None:
    if not payload:
        return None
    try:
        codepoint = int(payload, 16)
    except ValueError:
        return None
    if codepoint < 0 or codepoint > 0x10FFFF:
        return None
    try:
        return chr(codepoint)
    except ValueError:
        return None


def encode_line_escapes(text: str) -> str:
    """
    Convert multiline encoded text to a single line:
    - newline -> %n
    - literal % -> %p
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []
    for ch in normalized:
        if ch == LINE_ESCAPE_MARKER:
            out.append(LINE_ESCAPE_MARKER + LINE_ESCAPE_PERCENT)
        elif ch == "\n":
            out.append(LINE_ESCAPE_MARKER + LINE_ESCAPE_NEWLINE)
        else:
            out.append(ch)
    return "".join(out)


def decode_line_escapes(text: str) -> str:
    """
    Reverse `encode_line_escapes`:
    - %n -> newline
    - %p -> %
    Any unknown %<x> sequence is left as-is.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != LINE_ESCAPE_MARKER or i + 1 >= n:
            out.append(ch)
            i += 1
            continue

        tag = text[i + 1]
        if tag == LINE_ESCAPE_NEWLINE:
            out.append("\n")
            i += 2
            continue
        if tag == LINE_ESCAPE_PERCENT:
            out.append(LINE_ESCAPE_MARKER)
            i += 2
            continue

        # Keep unknown sequences unchanged.
        out.append(LINE_ESCAPE_MARKER)
        i += 1

    return "".join(out)


def generate_lookup_candidates(word: str) -> list[str]:
    """
    Build ordered candidates to resolve orthographic/colloquial variants
    to one canonical dictionary entry.
    """
    base = normalize_word(word)
    if not base:
        return []

    queue: list[str] = []
    mapped = COLLOQUIAL_EXACT_MAP.get(base.replace(ZWNJ, ""))
    if mapped:
        queue.append(mapped)
    queue.append(base)
    seen: set[str] = set()
    candidates: list[str] = []

    while queue and len(candidates) < MAX_LOOKUP_CANDIDATES:
        cur = normalize_word(queue.pop(0))
        if not cur or cur in seen:
            continue
        seen.add(cur)
        candidates.append(cur)

        for nxt in _direct_variants(cur):
            fixed = normalize_word(nxt)
            if fixed and fixed not in seen:
                queue.append(fixed)

    return candidates


def _direct_variants(word: str) -> list[str]:
    variants: list[str] = []

    # نیم‌فاصله variations
    if ZWNJ in word:
        variants.append(word.replace(ZWNJ, ""))

    _append_mi_variants(word, variants)
    _append_alef_madda_variants(word, variants)
    _append_hamza_ye_variants(word, variants)

    compact = word.replace(ZWNJ, "")
    mapped = COLLOQUIAL_EXACT_MAP.get(compact)
    if mapped:
        variants.append(mapped)

    # Generic rule for start-of-word colloquial "اومد..." -> "آمد..."
    if compact.startswith("اومد"):
        variants.append("آمد" + compact[4:])

    # Generic rule for missing madda in "امد..." -> "آمد..."
    if compact.startswith("امد"):
        variants.append("آمد" + compact[3:])

    return variants


def _append_mi_variants(word: str, out: list[str]) -> None:
    mi_joined = "می" + ZWNJ
    nemi_joined = "نمی" + ZWNJ

    if word.startswith(mi_joined):
        out.append("می" + word[len(mi_joined) :])
    elif word.startswith("می") and len(word) > 2:
        out.append(mi_joined + word[2:])

    if word.startswith(nemi_joined):
        out.append("نمی" + word[len(nemi_joined) :])
    elif word.startswith("نمی") and len(word) > 3:
        out.append(nemi_joined + word[3:])


def _append_alef_madda_variants(word: str, out: list[str]) -> None:
    if "آ" in word:
        out.append(word.replace("آ", "ا"))

    # Build a few candidates where one alef is replaced by alef-madda.
    for idx, ch in enumerate(word):
        if ch == "ا":
            out.append(word[:idx] + "آ" + word[idx + 1 :])


def _append_hamza_ye_variants(word: str, out: list[str]) -> None:
    if "ئ" in word:
        out.append(word.replace("ئ", "ی"))

    for idx, ch in enumerate(word):
        if ch == "ی":
            out.append(word[:idx] + "ئ" + word[idx + 1 :])


def is_persian_word(token: str) -> bool:
    if not PERSIAN_WORD_RE.match(token):
        return False
    normalized = normalize_word(token)
    return bool(NORMALIZED_PERSIAN_WORD_RE.match(normalized))
