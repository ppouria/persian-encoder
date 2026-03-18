from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests

HAZM_WORDS_URL = "https://raw.githubusercontent.com/sobhe/hazm/master/hazm/data/words.dat"
ZWNJ = "\u200c"
PERSIAN_RE = re.compile(rf"^[آ-ی]+(?:{ZWNJ}[آ-ی]+)*$")
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
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
        "ـ": "",
    }
)


def normalize_word(word: str) -> str:
    normalized = word.strip().translate(NORMALIZATION_TABLE)
    normalized = DIACRITICS_RE.sub("", normalized)
    normalized = MULTI_ZWNJ_RE.sub(ZWNJ, normalized)
    return normalized


def load_hazm_words() -> dict[str, int]:
    text = requests.get(HAZM_WORDS_URL, timeout=60).text
    best: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        word = normalize_word(parts[0])
        if not word or not PERSIAN_RE.match(word):
            continue
        try:
            freq = int(parts[1])
        except ValueError:
            continue
        prev = best.get(word)
        if prev is None or freq > prev:
            best[word] = freq
    return best


def word_score(word: str, freq: int) -> int:
    # Prefer frequently used + longer words for better compression value.
    return freq * max(1, len(word) - 1)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Build a large Persian wordbank from Hazm.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("persian_encoder/data/hazm_words.tsv"),
        help="Output TSV path (word<TAB>frequency).",
    )
    parser.add_argument("--top", type=int, default=25000, help="How many ranked words to keep.")
    parser.add_argument("--min-len", type=int, default=2, help="Minimum word length.")
    parser.add_argument("--min-freq", type=int, default=1, help="Minimum frequency threshold.")
    args = parser.parse_args()

    word_freq = load_hazm_words()
    ranked: list[tuple[int, int, str]] = []
    for word, freq in word_freq.items():
        if len(word) < args.min_len or freq < args.min_freq:
            continue
        ranked.append((word_score(word, freq), freq, word))

    ranked.sort(reverse=True)
    picked = ranked[: args.top]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for _score, freq, word in picked:
            handle.write(f"{word}\t{freq}\n")

    print(f"source={HAZM_WORDS_URL}")
    print(f"total_unique={len(word_freq)}")
    print(f"selected={len(picked)}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()

