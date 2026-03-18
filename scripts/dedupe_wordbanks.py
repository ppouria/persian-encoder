from __future__ import annotations

import argparse
from pathlib import Path


def extract_word(line: str, *, is_tsv: bool) -> str:
    if is_tsv:
        return line.split("\t", 1)[0].strip()
    return line.strip()


def dedupe_files(paths: list[Path]) -> None:
    seen_global: set[str] = set()
    total_kept = 0
    total_removed = 0

    for path in paths:
        if not path.is_file():
            print(f"skip_missing path={path}")
            continue

        is_tsv = path.suffix.lower() == ".tsv"
        kept_lines: list[str] = []
        removed = 0
        total = 0

        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue

                total += 1
                word = extract_word(line, is_tsv=is_tsv)
                if not word:
                    continue

                if word in seen_global:
                    removed += 1
                    continue

                seen_global.add(word)
                kept_lines.append(line if is_tsv else word)

        with path.open("w", encoding="utf-8", newline="\n") as handle:
            if kept_lines:
                handle.write("\n".join(kept_lines) + "\n")
            else:
                handle.write("")

        kept = len(kept_lines)
        total_kept += kept
        total_removed += removed
        print(f"path={path} total={total} kept={kept} removed={removed}")

    print(f"done files={len(paths)} kept_total={total_kept} removed_total={total_removed}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove duplicate words across wordbank files in order."
    )
    parser.add_argument(
        "--files",
        nargs="+",
        type=Path,
        default=[
            Path("persian_encoder/data/priority_words.tsv"),
            Path("persian_encoder/data/hazm_words.tsv"),
            Path("persian_encoder/data/seed_words.txt"),
        ],
        help="Wordbank files in precedence order. Earlier files keep duplicates; later files drop them.",
    )
    args = parser.parse_args()
    dedupe_files(args.files)


if __name__ == "__main__":
    main()
