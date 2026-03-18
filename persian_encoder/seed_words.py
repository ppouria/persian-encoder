from __future__ import annotations

from importlib.resources import files

from .large_words import get_large_words


def _load_text_words(relative_path: str) -> list[str]:
    resource = files("persian_encoder").joinpath(relative_path)
    if not resource.is_file():
        return []

    seen: set[str] = set()
    output: list[str] = []

    with resource.open("r", encoding="utf-8") as handle:
        for raw in handle:
            word = raw.strip()
            if not word or word in seen:
                continue
            seen.add(word)
            output.append(word)

    return output


def _load_tsv_words(relative_path: str) -> list[str]:
    resource = files("persian_encoder").joinpath(relative_path)
    if not resource.is_file():
        return []

    seen: set[str] = set()
    output: list[str] = []

    with resource.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            word = line.split("\t", 1)[0].strip()
            if not word or word in seen:
                continue
            seen.add(word)
            output.append(word)

    return output


def get_priority_words() -> list[str]:
    return _load_tsv_words("data/priority_words.tsv")


def get_extra_seed_words() -> list[str]:
    return _load_text_words("data/seed_words.txt")


def get_seed_words() -> list[str]:
    seen: set[str] = set()
    output: list[str] = []

    # Priority order: ranked words first for minimal practical text size.
    for word in get_priority_words():
        if word in seen:
            continue
        seen.add(word)
        output.append(word)

    # Then keep broad-coverage banks.
    for word in get_large_words():
        if word in seen:
            continue
        seen.add(word)
        output.append(word)

    for word in get_extra_seed_words():
        if word in seen:
            continue
        seen.add(word)
        output.append(word)

    return output
