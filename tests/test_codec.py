from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from persian_encoder import PersianEncoder
from persian_encoder.seed_words import get_priority_words
from persian_encoder.utils import decode_line_escapes, encode_line_escapes


class PersianEncoderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        db_path = Path(self.tmp.name) / "lexicon.db"
        self.encoder = PersianEncoder(db_path=db_path)

    def tearDown(self) -> None:
        self.encoder.close()
        self.tmp.cleanup()

    def test_known_words_encode_decode(self) -> None:
        text = "سلام دنیا"
        encoded = self.encoder.encode(text)
        self.assertNotEqual(encoded, text)
        self.assertEqual(self.encoder.decode(encoded), text)

    def test_unknown_word_roundtrip(self) -> None:
        text = "سلام ژپغژپغ"
        encoded = self.encoder.encode(text)
        self.assertNotIn("~uژپغژپغ", encoded)
        self.assertEqual(self.encoder.decode(encoded), text)

    def test_unknown_word_marker_mode(self) -> None:
        self.encoder.close()
        db_path = Path(self.tmp.name) / "lexicon.db"
        self.encoder = PersianEncoder(db_path=db_path, encode_unknown_words=True, prefer_smaller_output=False)
        text = "سلام ژپغژپغ"
        encoded = self.encoder.encode(text)
        self.assertIn("~U", encoded)
        self.assertNotEqual(encoded, text)
        self.assertEqual(self.encoder.decode(encoded), text)

    def test_unknown_word_marker_mode_ignores_size_preference(self) -> None:
        self.encoder.close()
        db_path = Path(self.tmp.name) / "lexicon.db"
        self.encoder = PersianEncoder(db_path=db_path, encode_unknown_words=True, prefer_smaller_output=True)
        text = "ژپغژپغ"
        encoded = self.encoder.encode(text)
        self.assertTrue(encoded.startswith("~U"))
        self.assertEqual(self.encoder.decode(encoded), text)

    def test_ascii_only_encode_has_no_non_ascii_chars(self) -> None:
        self.encoder.close()
        db_path = Path(self.tmp.name) / "lexicon.db"
        self.encoder = PersianEncoder(db_path=db_path, ascii_only=True)
        text = "سلام، دنیا 😊 ۱۴۰۴ café"
        encoded = self.encoder.encode(text)
        self.assertTrue(all(ord(ch) < 128 for ch in encoded))
        decoded = self.encoder.decode(encoded)
        self.assertEqual(decoded, "سلام, دنیا 😊 1404 café")

    def test_ascii_only_encodes_unknown_persian_words_without_flag(self) -> None:
        self.encoder.close()
        db_path = Path(self.tmp.name) / "lexicon.db"
        self.encoder = PersianEncoder(db_path=db_path, ascii_only=True)
        encoded = self.encoder.encode("ژپغژپغ")
        self.assertTrue(encoded.startswith("~U"))
        self.assertEqual(self.encoder.decode(encoded), "ژپغژپغ")

    def test_punctuation_preserved(self) -> None:
        text = "سلام، حالت چطوره؟"
        encoded = self.encoder.encode(text)
        decoded = self.encoder.decode(encoded)
        self.assertEqual(decoded, "سلام, حالت چطوره?")

    def test_add_word_changes_encoding(self) -> None:
        text = "ژپغژپغ"
        encoded_before = self.encoder.encode(text)
        self.assertEqual(self.encoder.decode(encoded_before), text)

        code = self.encoder.add_word(text)
        self.assertTrue(code.startswith("s"))

        encoded_after = self.encoder.encode(text)
        self.assertEqual(encoded_after, f"~{code[1:]}")
        self.assertLessEqual(len(encoded_after), len(encoded_before))
        self.assertEqual(self.encoder.decode(encoded_after), text)

    def test_persian_digits_normalized_to_ascii(self) -> None:
        text = "سال ۱۴۰۴ و ٢٠٢٦"
        encoded = self.encoder.encode(text)
        self.assertIn("1404", encoded)
        self.assertIn("2026", encoded)
        self.assertEqual(self.encoder.decode(encoded), "سال 1404 و 2026")

    def test_subword_suffix_uses_ascii_marker(self) -> None:
        encoded = self.encoder.encode("دانشگاهی")
        self.assertIn("Y", encoded)
        self.assertIn("_", encoded)
        self.assertIn(";", encoded)
        self.assertEqual(self.encoder.decode(encoded), "دانشگاهی")

    def test_diacritic_word_encodes_cleanly(self) -> None:
        encoded = self.encoder.encode("سَلام")
        self.assertTrue(encoded.startswith("~"))
        self.assertEqual(self.encoder.decode(encoded), "سلام")

    def test_amad_variants_share_same_code(self) -> None:
        code_standard = self.encoder.db.get_code("آمدم")
        code_no_madda = self.encoder.db.get_code("امدم")
        code_colloquial = self.encoder.db.get_code("اومدم")

        self.assertIsNotNone(code_standard)
        self.assertEqual(code_no_madda, code_standard)
        self.assertEqual(code_colloquial, code_standard)

        force_encoder = PersianEncoder(
            db_path=Path(self.tmp.name) / "lexicon.db",
            prefer_smaller_output=False,
        )
        try:
            encoded = force_encoder.encode("امدم اومدم")
            self.assertNotIn("~u", encoded)
            self.assertEqual(force_encoder.decode(encoded), "آمدم آمدم")
        finally:
            force_encoder.close()

    def test_mi_spacing_variants_share_same_code(self) -> None:
        code_plain = self.encoder.db.get_code("میشد")
        code_joined = self.encoder.db.get_code("می‌شد")
        self.assertIsNotNone(code_plain)
        self.assertEqual(code_joined, code_plain)

        encoded = self.encoder.encode("میشد می‌شد")
        self.assertNotIn("~u", encoded)
        self.assertEqual(self.encoder.decode(encoded), "میشد میشد")

    def test_colloquial_khastan_variant_maps_to_canonical(self) -> None:
        code_standard = self.encoder.db.get_code("میخواهم")
        code_colloquial = self.encoder.db.get_code("میخوام")
        self.assertIsNotNone(code_standard)
        self.assertEqual(code_colloquial, code_standard)

        encoded = self.encoder.encode("میخوام")
        self.assertNotIn("~u", encoded)
        self.assertEqual(self.encoder.decode(encoded), "میخواهم")

    def test_alef_madda_variants_share_same_code(self) -> None:
        code_with_madda = self.encoder.db.get_code("آسان")
        code_without_madda = self.encoder.db.get_code("اسان")
        self.assertIsNotNone(code_with_madda)
        self.assertEqual(code_without_madda, code_with_madda)

        force_encoder = PersianEncoder(
            db_path=Path(self.tmp.name) / "lexicon.db",
            prefer_smaller_output=False,
        )
        try:
            encoded = force_encoder.encode("اسان")
            self.assertNotIn("~u", encoded)
            self.assertEqual(force_encoder.decode(encoded), "آسان")
        finally:
            force_encoder.close()

    def test_hamza_ye_variants_share_same_code(self) -> None:
        code_no_hamza = self.encoder.db.get_code("اسراییل")
        code_with_hamza = self.encoder.db.get_code("اسرائیل")
        self.assertIsNotNone(code_no_hamza)
        self.assertEqual(code_with_hamza, code_no_hamza)

        encoded = self.encoder.encode("اسرائیل")
        self.assertNotIn("~u", encoded)
        self.assertIn(self.encoder.decode(encoded), {"اسراییل", "اسرائیل"})

    def test_mixed_english_persian_text_roundtrip(self) -> None:
        text = "Breaking News: سلام to all, update در Tehran 2026."
        encoded = self.encoder.encode(text)
        self.assertIn("Breaking News:", encoded)
        self.assertIn("Tehran 2026.", encoded)
        self.assertEqual(self.encoder.decode(encoded), text)

    def test_utf8_mixed_symbols_roundtrip(self) -> None:
        text = "سلام 😊 café update"
        encoded = self.encoder.encode(text)
        decoded = self.encoder.decode(encoded)
        self.assertEqual(decoded, text)

    def test_colloquial_words_map_to_canonical(self) -> None:
        encoded = self.encoder.encode("می‌کنه خیابون اتیش")
        self.assertNotIn("~u", encoded)
        self.assertEqual(self.encoder.decode(encoded), "میکند خیابان آتش")

    def test_colloquial_short_words_in_force_mode(self) -> None:
        self.encoder.close()
        db_path = Path(self.tmp.name) / "lexicon.db"
        self.encoder = PersianEncoder(db_path=db_path, prefer_smaller_output=False)
        encoded = self.encoder.encode("رو داره")
        self.assertEqual(self.encoder.decode(encoded), "را دارد")

    def test_short_words_left_raw_when_not_smaller(self) -> None:
        text = "و در به از"
        encoded = self.encoder.encode(text)
        self.assertLessEqual(len(encoded), len(text))
        self.assertEqual(self.encoder.decode(encoded), text)

    def test_long_word_is_encoded_when_smaller(self) -> None:
        text = "دانشگاه"
        encoded = self.encoder.encode(text)
        self.assertTrue(encoded.startswith("~"))
        self.assertEqual(self.encoder.decode(encoded), text)

    def test_folded_space_marker_used_for_better_compression(self) -> None:
        text = "و در به دانشگاه زیرساخت"
        encoded = self.encoder.encode(text)
        self.assertIn("^", encoded)
        self.assertLess(len(encoded), len(text))
        self.assertEqual(self.encoder.decode(encoded), text)

    def test_decode_legacy_marker_format(self) -> None:
        code = self.encoder.db.get_code("دانشگاه")
        self.assertIsNotNone(code)
        self.assertEqual(self.encoder.decode(f"~{code}"), "دانشگاه")

    def test_decode_legacy_unknown_marker_format(self) -> None:
        self.assertEqual(self.encoder.decode("~uسلام"), "سلام")

    def test_priority_words_start_from_smallest_codes(self) -> None:
        ranked = get_priority_words()
        self.assertGreaterEqual(len(ranked), 2)
        code1 = self.encoder.db.get_code(ranked[0])
        code2 = self.encoder.db.get_code(ranked[1])
        self.assertEqual(code1, "s1")
        self.assertEqual(code2, "s2")

    def test_subword_suffix_encoding(self) -> None:
        encoded = self.encoder.encode("دانشگاهی")
        self.assertIn("دانشگاه", self.encoder.decode(encoded))
        self.assertLess(len(encoded), len("دانشگاهی"))
        self.assertEqual(self.encoder.decode(encoded), "دانشگاهی")

    def test_subword_suffix_encoding_with_space_fold(self) -> None:
        text = "این دانشگاهی عالی است"
        encoded = self.encoder.encode(text)
        self.assertIn("^", encoded)
        self.assertEqual(self.encoder.decode(encoded), text)

    def test_rebuild_dictionary_keeps_working(self) -> None:
        before = self.encoder.dictionary_size()
        rebuilt = self.encoder.rebuild_dictionary()
        after = self.encoder.dictionary_size()
        self.assertEqual(rebuilt, before)
        self.assertEqual(after, before)
        text = "دانشگاه زیرساخت"
        self.assertEqual(self.encoder.decode(self.encoder.encode(text)), text)

    def test_pack_roundtrip(self) -> None:
        text = "و در به دانشگاه زیرساخت و Breaking News Tehran"
        packed = self.encoder.encode_pack(text)
        decoded = self.encoder.decode_pack(packed)
        self.assertEqual(decoded, text)

    def test_decode_compact_code_with_trailing_digits(self) -> None:
        code = self.encoder.db.get_code("اسفند")
        self.assertIsNotNone(code)
        compact = code[1:]
        decoded = self.encoder.decode(f"27~{compact}1404")
        self.assertEqual(decoded, "27اسفند1404")

    def test_line_escape_roundtrip(self) -> None:
        original = "~1\n~2\n100% done"
        escaped = encode_line_escapes(original)
        self.assertEqual(escaped, "~1%n~2%n100%p done")
        self.assertEqual(decode_line_escapes(escaped), original)

    def test_line_escape_unknown_sequence_kept(self) -> None:
        self.assertEqual(decode_line_escapes("abc%zdef"), "abc%zdef")


if __name__ == "__main__":
    unittest.main()
