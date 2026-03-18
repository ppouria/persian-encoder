from __future__ import annotations

import base64
import zlib

PACKED_PREFIX = "z"
RAW_PREFIX = "n"


def compress_encoded_text(encoded_text: str, *, level: int = 9) -> str:
    raw = encoded_text.encode("utf-8")
    compressed = zlib.compress(raw, level=level)
    payload = base64.b85encode(compressed).decode("ascii")
    candidate = PACKED_PREFIX + payload
    fallback = RAW_PREFIX + encoded_text
    return candidate if len(candidate) < len(fallback) else fallback


def decompress_encoded_text(packed_text: str) -> str:
    if not packed_text:
        return packed_text

    mode = packed_text[0]
    payload = packed_text[1:]

    if mode == RAW_PREFIX:
        return payload

    if mode == PACKED_PREFIX:
        compressed = base64.b85decode(payload.encode("ascii"))
        return zlib.decompress(compressed).decode("utf-8")

    # Backward-compatible fallback: treat as already encoded text.
    return packed_text


def compress_encoded_bytes(encoded_text: str, *, level: int = 9) -> bytes:
    return zlib.compress(encoded_text.encode("utf-8"), level=level)


def decompress_encoded_bytes(data: bytes) -> str:
    return zlib.decompress(data).decode("utf-8")

