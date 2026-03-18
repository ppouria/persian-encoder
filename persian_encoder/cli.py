from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .codec import PersianEncoder
from .utils import decode_line_escapes, encode_line_escapes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="persian-encoder",
        description="Encode/decode Persian text with a SQLite dictionary.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite dictionary file (default: ~/.persian_encoder/lexicon.db)",
    )
    parser.add_argument(
        "--metric",
        choices=["bytes", "chars"],
        default="chars",
        help="Size metric for hybrid encoding (default: chars).",
    )
    parser.add_argument(
        "--force-encode",
        action="store_true",
        help="Encode known words even when result is not smaller.",
    )
    parser.add_argument(
        "--unknown-marker",
        action="store_true",
        help="Encode unknown Persian words as ASCII-safe ~U<payload>; format.",
    )
    parser.add_argument(
        "--ascii-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="ASCII-only encoded output (default: on). Use --no-ascii-only to keep Unicode output.",
    )
    parser.add_argument(
        "--single-line",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use %n/%p line escaping in CLI (default: on). Use --no-single-line for raw newlines.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    encode_cmd = subparsers.add_parser("encode", help="Encode text")
    encode_cmd.add_argument("text", help="Input text")

    decode_cmd = subparsers.add_parser("decode", help="Decode encoded text")
    decode_cmd.add_argument("text", help="Encoded input")

    pack_cmd = subparsers.add_parser("encode-pack", help="Encode then smart-compress output")
    pack_cmd.add_argument("text", help="Input text")
    pack_cmd.add_argument(
        "--level",
        type=int,
        default=9,
        help="zlib compression level (0-9, default: 9)",
    )

    unpack_cmd = subparsers.add_parser("decode-pack", help="Decompress packed text then decode")
    unpack_cmd.add_argument("text", help="Packed input text")

    add_cmd = subparsers.add_parser("add-word", help="Add new dictionary word")
    add_cmd.add_argument("word", help="Persian word to add")
    add_cmd.add_argument("--code", default=None, help="Optional fixed code (example: s9999)")

    subparsers.add_parser("rebuild", help="Rebuild dictionary codes for denser ids")
    subparsers.add_parser("stats", help="Show dictionary stats")
    return parser


def main() -> None:
    # Avoid UnicodeEncodeError on Windows terminals configured with non-UTF8 codepages.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()
    engine = PersianEncoder(
        db_path=args.db,
        prefer_smaller_output=not args.force_encode,
        size_metric=args.metric,
        encode_unknown_words=args.unknown_marker,
        ascii_only=args.ascii_only,
    )

    try:
        if args.command == "encode":
            encoded = engine.encode(args.text)
            if args.single_line:
                encoded = encode_line_escapes(encoded)
            print(encoded)
            return

        if args.command == "decode":
            encoded_input = decode_line_escapes(args.text) if args.single_line else args.text
            print(engine.decode(encoded_input))
            return

        if args.command == "encode-pack":
            print(engine.encode_pack(args.text, level=max(0, min(9, args.level))))
            return

        if args.command == "decode-pack":
            print(engine.decode_pack(args.text))
            return

        if args.command == "add-word":
            code = engine.add_word(args.word, code=args.code)
            print(f"{args.word} => {code}")
            return

        if args.command == "rebuild":
            count = engine.rebuild_dictionary()
            print(f"rebuild_done words={count}")
            return

        if args.command == "stats":
            print(f"dictionary_size={engine.dictionary_size()}")
            return

        parser.error(f"Unknown command: {args.command}")
    finally:
        engine.close()


if __name__ == "__main__":
    main()
