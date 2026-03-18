from __future__ import annotations

from pathlib import Path

from .database import WordDatabase
from .packing import (
    compress_encoded_bytes,
    compress_encoded_text,
    decompress_encoded_bytes,
    decompress_encoded_text,
)
from .utils import (
    CODE_CHARS,
    ENCODE_SOURCE_TOKEN_RE,
    KNOWN_CODE_PREFIX,
    KNOWN_MARKER,
    KNOWN_SPACE_MARKER,
    SUBWORD_ASCII_END,
    SUBWORD_ASCII_ESCAPE,
    SUBWORD_ASCII_MARKER,
    UNKNOWN_ASCII_CODE_PREFIX,
    UNKNOWN_ASCII_END,
    UNKNOWN_CODE_PREFIX,
    UNICODE_ESCAPE_END,
    UNICODE_ESCAPE_PREFIX,
    decode_ascii_fragment,
    decode_unicode_escape_payload,
    decode_unknown_ascii_word,
    escape_non_ascii_text,
    encode_ascii_fragment,
    encode_unknown_ascii_word,
    is_persian_word,
    normalize_non_persian_chunk,
    normalize_word,
)


class PersianEncoder:
    """
    Persian word-level encoder/decoder.

    Encoding format:
    - Known word from DB: `~<id>` (example: `~1`)
    - Known word with one folded leading space: `^<id>` (example: `^1`)
    - Unknown Persian word (optional mode): `~U<ascii_payload>;`
      (legacy decode remains compatible with `~u<word>`)
    - Generic non-ASCII escape in ASCII-only mode: `~X<hex_codepoint>;`

    Default behavior is hybrid compression:
    - encode only if encoded token is smaller
    - unknown words stay raw unless `encode_unknown_words=True`
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        prefer_smaller_output: bool = True,
        size_metric: str = "chars",
        encode_unknown_words: bool = False,
        ascii_only: bool = False,
    ) -> None:
        self.db = WordDatabase(db_path=db_path)
        self.prefer_smaller_output = prefer_smaller_output
        self.size_metric = size_metric
        self.encode_unknown_words = encode_unknown_words
        self.ascii_only = ascii_only

        if self.size_metric not in {"bytes", "chars"}:
            raise ValueError("size_metric must be either 'bytes' or 'chars'")

    def encode(self, text: str) -> str:
        parts: list[str] = []
        for token in ENCODE_SOURCE_TOKEN_RE.findall(text):
            if not is_persian_word(token):
                chunk = normalize_non_persian_chunk(token)
                if self.ascii_only:
                    chunk = escape_non_ascii_text(chunk)
                parts.append(chunk)
                continue

            normalized_token = normalize_word(token)
            if not normalized_token:
                continue

            selected = self._select_best_known_encoding(
                normalized_token,
                parts,
                prefer_smaller=(self.prefer_smaller_output and not self.ascii_only),
            )
            if selected:
                encoded_value, uses_folded_space = selected
                if uses_folded_space:
                    self._remove_one_trailing_space(parts)
                parts.append(encoded_value)
                continue

            if not self.encode_unknown_words and not self.ascii_only:
                parts.append(normalized_token)
                continue

            ascii_payload = encode_unknown_ascii_word(normalized_token)
            if ascii_payload:
                parts.append(
                    f"{KNOWN_MARKER}{UNKNOWN_ASCII_CODE_PREFIX}{ascii_payload}{UNKNOWN_ASCII_END}"
                )
                continue

            # Fallback paths:
            # - ASCII-only: escape as generic Unicode sequences.
            # - Normal mode: keep legacy unknown marker for compatibility.
            if self.ascii_only:
                parts.append(escape_non_ascii_text(normalized_token))
            else:
                parts.append(f"{KNOWN_MARKER}{UNKNOWN_CODE_PREFIX}{normalized_token}")
        return "".join(parts)

    def decode(self, encoded_text: str) -> str:
        result: list[str] = []
        i = 0
        n = len(encoded_text)

        while i < n:
            ch = encoded_text[i]

            # Compact format with folded one leading space: ^<code>
            if ch == KNOWN_SPACE_MARKER and i + 1 < n:
                j = i + 1
                while j < n and encoded_text[j] in CODE_CHARS:
                    j += 1
                if j > i + 1:
                    compact = encoded_text[i + 1 : j]
                    resolved = self._resolve_compact_code(compact)
                    if resolved:
                        word, consumed = resolved
                        code_end = i + 1 + consumed
                        suffix, end_idx = self._consume_ascii_suffix(encoded_text, code_end)
                        result.append(" " + word + suffix)
                        i = end_idx
                        continue

            if ch != KNOWN_MARKER or i + 1 >= n:
                result.append(encoded_text[i])
                i += 1
                continue

            tag = encoded_text[i + 1]

            if tag == UNICODE_ESCAPE_PREFIX:
                end = encoded_text.find(UNICODE_ESCAPE_END, i + 2)
                if end > i + 2:
                    payload = encoded_text[i + 2 : end]
                    decoded = decode_unicode_escape_payload(payload)
                    if decoded is not None:
                        result.append(decoded)
                        i = end + 1
                        continue

            if tag == UNKNOWN_ASCII_CODE_PREFIX:
                end = encoded_text.find(UNKNOWN_ASCII_END, i + 2)
                if end > i + 2:
                    payload = encoded_text[i + 2 : end]
                    decoded = decode_unknown_ascii_word(payload)
                    if decoded is not None:
                        result.append(decoded)
                        i = end + 1
                        continue

            if tag == UNKNOWN_CODE_PREFIX:
                j = self._consume_persian_word(encoded_text, i + 2)
                if j > i + 2:
                    result.append(encoded_text[i + 2 : j])
                    i = j
                    continue

            if tag == KNOWN_CODE_PREFIX:
                j = i + 2
                while j < n and encoded_text[j] in CODE_CHARS:
                    j += 1
                if j > i + 2:
                    code = f"{KNOWN_CODE_PREFIX}{encoded_text[i + 2 : j]}"
                    word = self.db.get_word(code)
                    if word:
                        suffix, end_idx = self._consume_ascii_suffix(encoded_text, j)
                        result.append(word + suffix)
                        i = end_idx
                        continue

            # New compact known-code format: ~<code>
            j = i + 1
            while j < n and encoded_text[j] in CODE_CHARS:
                j += 1
            if j > i + 1:
                compact = encoded_text[i + 1 : j]
                resolved = self._resolve_compact_code(compact)
                if resolved:
                    word, consumed = resolved
                    code_end = i + 1 + consumed
                    suffix, end_idx = self._consume_ascii_suffix(encoded_text, code_end)
                    result.append(word + suffix)
                    i = end_idx
                    continue

            # Invalid marker sequence, keep raw marker
            result.append(encoded_text[i])
            i += 1

        return "".join(result)

    def add_word(self, word: str, code: str | None = None) -> str:
        return self.db.add_word(word=word, code=code)

    def dictionary_size(self) -> int:
        return self.db.count()

    def rebuild_dictionary(self) -> int:
        return self.db.rebuild_codes()

    def encode_pack(self, text: str, *, level: int = 9) -> str:
        encoded = self.encode(text)
        return compress_encoded_text(encoded, level=level)

    def decode_pack(self, packed_text: str) -> str:
        encoded = decompress_encoded_text(packed_text)
        return self.decode(encoded)

    def encode_pack_bytes(self, text: str, *, level: int = 9) -> bytes:
        encoded = self.encode(text)
        return compress_encoded_bytes(encoded, level=level)

    def decode_pack_bytes(self, packed_bytes: bytes) -> str:
        encoded = decompress_encoded_bytes(packed_bytes)
        return self.decode(encoded)

    def close(self) -> None:
        self.db.close()

    def _is_smaller(self, original: str, encoded: str) -> bool:
        if self.size_metric == "chars":
            return len(encoded) < len(original)
        return len(encoded.encode("utf-8")) < len(original.encode("utf-8"))

    def _select_best_known_encoding(
        self,
        token: str,
        parts: list[str],
        *,
        prefer_smaller: bool | None = None,
    ) -> tuple[str, bool] | None:
        can_fold_space = self._can_fold_space(parts)
        candidates = self._build_known_candidates(token)
        if not candidates:
            return None

        scored: list[tuple[int, int, int, str, bool]] = []
        for priority, candidate in enumerate(candidates):
            if candidate.startswith(KNOWN_MARKER):
                # Plain marker form, no space fold.
                plain_delta = self._size_delta(token, candidate)
                scored.append((plain_delta, self._size(candidate), priority, candidate, False))

                # Space-folded marker form.
                if can_fold_space:
                    folded = KNOWN_SPACE_MARKER + candidate[1:]
                    folded_delta = self._size_delta(f" {token}", folded)
                    scored.append((folded_delta, self._size(folded), priority, folded, True))
                continue

            # Composite starting with raw prefix (cannot fold leading space).
            delta = self._size_delta(token, candidate)
            scored.append((delta, self._size(candidate), priority, candidate, False))

        use_prefer_smaller = self.prefer_smaller_output if prefer_smaller is None else prefer_smaller

        if use_prefer_smaller:
            scored = [item for item in scored if item[0] > 0]
            if not scored:
                return None
            # Bigger gain first, then shorter encoding, then earlier candidate priority.
            scored.sort(key=lambda item: (-item[0], item[1], item[2]))
            _delta, _size, _priority, encoded_value, uses_folded_space = scored[0]
            return encoded_value, uses_folded_space

        # Force mode: pick shortest encoded candidate.
        scored.sort(key=lambda item: (item[1], -item[0], item[2]))
        _delta, _size, _priority, encoded_value, uses_folded_space = scored[0]
        return encoded_value, uses_folded_space

    def _build_known_candidates(self, token: str) -> list[str]:
        candidates: list[str] = []
        seen: set[str] = set()

        exact_code = self.db.get_code(token)
        if exact_code:
            encoded = f"{KNOWN_MARKER}{self._compact_code(exact_code)}"
            candidates.append(encoded)
            seen.add(encoded)

        # Composite candidates: encode known subword inside token (prefix/suffix/both).
        for split in range(1, len(token)):
            left = token[:split]
            right = token[split:]

            left_code = self.db.get_code(left) if len(left) >= 2 else None

            if left_code:
                ascii_right = encode_ascii_fragment(right)
                if ascii_right is None:
                    continue
                encoded = (
                    f"{KNOWN_MARKER}{self._compact_code(left_code)}"
                    f"{SUBWORD_ASCII_MARKER}{SUBWORD_ASCII_ESCAPE}{ascii_right}{SUBWORD_ASCII_END}"
                )
                if encoded not in seen:
                    seen.add(encoded)
                    candidates.append(encoded)

        return candidates

    def _size(self, text: str) -> int:
        if self.size_metric == "chars":
            return len(text)
        return len(text.encode("utf-8"))

    def _size_delta(self, original: str, encoded: str) -> int:
        return self._size(original) - self._size(encoded)

    @staticmethod
    def _compact_code(code: str) -> str:
        if code.startswith(KNOWN_CODE_PREFIX):
            return code[1:]
        return code

    @staticmethod
    def _can_fold_space(parts: list[str]) -> bool:
        return bool(parts and parts[-1].endswith(" "))

    @staticmethod
    def _remove_one_trailing_space(parts: list[str]) -> None:
        if not parts:
            return
        if not parts[-1].endswith(" "):
            return
        parts[-1] = parts[-1][:-1]
        if not parts[-1]:
            parts.pop()

    @staticmethod
    def _consume_persian_word(text: str, start: int) -> int:
        if start >= len(text):
            return start

        i = start
        if not _is_persian_char(text[i]):
            return start
        i += 1

        while i < len(text):
            ch = text[i]
            if ch == "\u200c" or _is_persian_char(ch):
                i += 1
                continue
            break

        return i

    @staticmethod
    def _consume_ascii_suffix(text: str, start: int) -> tuple[str, int]:
        if start >= len(text) or text[start] != SUBWORD_ASCII_MARKER:
            return "", start

        if start + 1 >= len(text) or text[start + 1] != SUBWORD_ASCII_ESCAPE:
            return "", start

        end = text.find(SUBWORD_ASCII_END, start + 2)
        if end < 0:
            return "", start

        payload = text[start + 2 : end]
        if not payload:
            return "", start

        decoded = decode_ascii_fragment(payload)
        if decoded is None:
            return "", start

        return decoded, end + 1

    def _resolve_compact_code(self, compact: str) -> tuple[str, int] | None:
        word = self.db.get_word_by_compact_code(compact)
        if word:
            return word, len(compact)

        # Legacy ambiguity recovery:
        # Older outputs may have no separator between a compact code and trailing digits
        # (example: "~i1404" meaning "~i" + "1404").
        if compact and compact[0].isalpha():
            first_digit = -1
            for idx, ch in enumerate(compact):
                if ch.isdigit():
                    first_digit = idx
                    break
            if first_digit > 0:
                prefix = compact[:first_digit]
                prefix_word = self.db.get_word_by_compact_code(prefix)
                if prefix_word:
                    return prefix_word, first_digit

        return None


def _is_persian_char(ch: str) -> bool:
    return "آ" <= ch <= "ی"
