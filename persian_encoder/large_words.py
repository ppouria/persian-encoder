from __future__ import annotations

from importlib.resources import files


def get_large_words() -> list[str]:
    """
    Load large Persian word bank extracted from Hazm words.dat.
    File format: word<TAB>frequency
    """
    resource = files("persian_encoder").joinpath("data/hazm_words.tsv")
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

