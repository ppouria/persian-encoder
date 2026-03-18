# Persian Encoder

A Python library and CLI for Persian text encoding/decoding with a SQLite-backed lexicon.

## Overview

`persian-encoder` performs word-level encoding for Persian text using short dictionary codes.
It also supports:

- Persian orthography normalization (Arabic/Persian variants, diacritics, ZWNJ normalization)
- colloquial variant lookup (e.g. `اومدم` -> canonical dictionary form)
- optional unknown-word encoding
- ASCII-only transport-safe output
- optional single-line CLI output for storage/transmission

## Installation

### From source (local development)

```bash
pip install -e .
```

### Build artifacts

```bash
py -3 -m build
```

This creates `dist/*.whl` and `dist/*.tar.gz`.

## How To Call It In A Project

Use the Python package `persian_encoder`.

```python
from persian_encoder import PersianEncoder

engine = PersianEncoder(
    db_path=None,                 # default: ~/.persian_encoder/lexicon.db
    prefer_smaller_output=True,   # hybrid compression behavior
    size_metric="chars",          # "chars" or "bytes"
    encode_unknown_words=False,   # unknown Persian words marker mode
    ascii_only=False,             # API default; CLI default is True
)

text = 'سلام دنیا 😊'
encoded = engine.encode(text)
decoded = engine.decode(encoded)

print(encoded)
print(decoded)

engine.close()
```

## Public API

Class: `PersianEncoder`

- `encode(text: str) -> str`
- `decode(encoded_text: str) -> str`
- `encode_pack(text: str, level: int = 9) -> str`
- `decode_pack(packed_text: str) -> str`
- `encode_pack_bytes(text: str, level: int = 9) -> bytes`
- `decode_pack_bytes(packed_bytes: bytes) -> str`
- `add_word(word: str, code: str | None = None) -> str`
- `dictionary_size() -> int`
- `rebuild_dictionary() -> int`
- `close() -> None`

## CLI

Entry points:

- `persian-encoder ...`
- `py -3 -m persian_encoder.cli ...`

### Commands

```bash
persian-encoder encode "..."
persian-encoder decode "..."
persian-encoder encode-pack "..."
persian-encoder decode-pack "..."
persian-encoder add-word "واژه"
persian-encoder rebuild
persian-encoder stats
```

### Global options

- `--db <path>`: custom SQLite path
- `--metric {chars,bytes}`
- `--force-encode`
- `--unknown-marker`
- `--ascii-only` / `--no-ascii-only`
- `--single-line` / `--no-single-line`

### CLI defaults

- `--ascii-only` is **enabled** by default.
- `--single-line` is **enabled** by default.

So by default, encoded output is ASCII and one line.

## Encoding Format

### Known dictionary words

- `~<compact_code>`
- `^<compact_code>` (same as above, but folds one leading space)

### Subword suffix encoding

- `~<compact_code>Y_<suffix_payload>;`

Example: a word with known prefix and unknown suffix.

### Unknown Persian words

- `~U<payload>;` (ASCII payload, reversible)
- Legacy decode compatibility: `~u<word>` is still accepted by decoder.

### Generic Unicode escape (ASCII-only mode)

- `~X<hex_codepoint>;`

Example: emoji in ASCII-only output.

## Single-Line Escaping (CLI)

When `--single-line` is enabled:

- newline -> `%n`
- literal `%` -> `%p`

Decoder reverses these before decoding.

## Important Normalization Notes

This project intentionally normalizes text. Therefore decode output may be canonicalized, not byte-identical to input.
Examples:

- `اسرائیل` may decode as `اسراییل`
- diacritics may be removed
- Persian punctuation/digits can be normalized during encode path

If exact visual-form preservation is required, keep this behavior in mind.

## Data Files

Packaged lexicon inputs live under:

- `persian_encoder/data/priority_words.tsv`
- `persian_encoder/data/hazm_words.tsv`
- `persian_encoder/data/seed_words.txt`

## Rebuild Dictionary

After changing word lists, rebuild code ranking:

```bash
persian-encoder rebuild
```

## Testing

```bash
py -3 -m unittest discover -s tests -q
```
