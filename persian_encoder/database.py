from __future__ import annotations

import sqlite3
from pathlib import Path

from .seed_words import get_seed_words
from .utils import (
    DEFAULT_DB_PATH,
    KNOWN_CODE_PREFIX,
    generate_lookup_candidates,
    is_persian_word,
    normalize_word,
)

BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


class WordDatabase:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._init_schema()
        self._seed_defaults()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS words (
                word TEXT PRIMARY KEY,
                code TEXT NOT NULL UNIQUE
            );

            CREATE INDEX IF NOT EXISTS idx_words_code ON words(code);
            """
        )
        self._conn.commit()

    def _seed_defaults(self) -> None:
        words = [normalize_word(w) for w in get_seed_words()]
        unique_words: list[str] = []
        seen: set[str] = set()
        for word in words:
            if word in seen or not is_persian_word(word):
                continue
            seen.add(word)
            unique_words.append(word)

        existing_rows = self._conn.execute("SELECT word FROM words;").fetchall()
        existing_words = {row[0] for row in existing_rows}
        next_id = self._max_code_id() + 1

        with self._conn:
            for word in unique_words:
                if word in existing_words:
                    continue
                code = f"{KNOWN_CODE_PREFIX}{self._int_to_base36(next_id)}"
                self._conn.execute("INSERT INTO words(word, code) VALUES(?, ?);", (word, code))
                next_id += 1

    def get_code(self, word: str) -> str | None:
        for candidate in generate_lookup_candidates(word):
            row = self._conn.execute(
                "SELECT code FROM words WHERE word = ?;",
                (candidate,),
            ).fetchone()
            if row:
                return row[0]
        return None

    def get_word(self, code: str) -> str | None:
        row = self._conn.execute(
            "SELECT word FROM words WHERE code = ?;",
            (code,),
        ).fetchone()
        return row[0] if row else None

    def get_word_by_compact_code(self, compact: str) -> str | None:
        # Compact format removes leading "s" from default dictionary codes.
        word = self.get_word(f"{KNOWN_CODE_PREFIX}{compact}")
        if word:
            return word
        return self.get_word(compact)

    def add_word(self, word: str, code: str | None = None) -> str:
        normalized = normalize_word(word.strip())
        if not is_persian_word(normalized):
            raise ValueError("word must be a Persian token (letters and optional نیم‌فاصله)")

        final_code = code.strip().lower() if code else self._next_code()
        if not self._is_valid_code(final_code):
            raise ValueError("code must look like s1, s2, s3, ...")

        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO words(word, code) VALUES(?, ?);",
                    (normalized, final_code),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("word or code already exists in dictionary") from exc
        return final_code

    def _next_code(self) -> str:
        next_id = self._max_code_id() + 1
        return f"{KNOWN_CODE_PREFIX}{self._int_to_base36(next_id)}"

    def _max_code_id(self) -> int:
        rows = self._conn.execute(
            "SELECT code FROM words WHERE code LIKE ?;",
            (f"{KNOWN_CODE_PREFIX}%",),
        ).fetchall()
        max_id = 0
        for row in rows:
            code_id = self._code_to_int(row[0])
            if code_id > max_id:
                max_id = code_id
        return max_id

    @staticmethod
    def _int_to_base36(value: int) -> str:
        if value <= 0:
            return "0"
        chars: list[str] = []
        current = value
        while current:
            current, rem = divmod(current, 36)
            chars.append(BASE36_ALPHABET[rem])
        return "".join(reversed(chars))

    @staticmethod
    def _base36_to_int(text: str) -> int | None:
        if not text:
            return None
        value = 0
        for ch in text:
            idx = BASE36_ALPHABET.find(ch)
            if idx < 0:
                return None
            value = value * 36 + idx
        return value

    @classmethod
    def _code_to_int(cls, code: str) -> int:
        if not code.startswith(KNOWN_CODE_PREFIX):
            return 0
        num = cls._base36_to_int(code[1:])
        return int(num or 0)

    @staticmethod
    def _is_valid_code(code: str) -> bool:
        if len(code) < 2:
            return False
        if not code.startswith(KNOWN_CODE_PREFIX):
            return False
        return code[1:].isalnum() and code[1:] == code[1:].lower()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM words;").fetchone()
        return int(row[0]) if row else 0

    def rebuild_codes(self) -> int:
        rows = self._conn.execute("SELECT word FROM words;").fetchall()
        current_words = {row[0] for row in rows}
        if not current_words:
            return 0

        seed_order = [normalize_word(w) for w in get_seed_words()]
        rank_map = {word: idx for idx, word in enumerate(seed_order)}
        max_rank = len(seed_order) + 1

        # Seed-ranked words first, then longer words first for better compression value.
        ordered = sorted(
            current_words,
            key=lambda w: (rank_map.get(w, max_rank), -len(w), w),
        )

        with self._conn:
            self._conn.execute("DELETE FROM words;")
            for idx, word in enumerate(ordered, start=1):
                code = f"{KNOWN_CODE_PREFIX}{self._int_to_base36(idx)}"
                self._conn.execute("INSERT INTO words(word, code) VALUES(?, ?);", (word, code))

        return len(ordered)

    def close(self) -> None:
        self._conn.close()
