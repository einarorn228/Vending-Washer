"""Unit tests for QR scanner ingress validation."""

import unittest
from unittest.mock import patch

import backend.controllers.qr_scanner as qr_scanner


class ScannerTokenFormatTests(unittest.TestCase):
    def test_local_eight_char_alphanumeric_accepted(self):
        self.assertTrue(qr_scanner._looks_like_scanner_token("Ab12Cd34"))

    def test_uuid_with_hyphens_accepted(self):
        self.assertTrue(
            qr_scanner._looks_like_scanner_token("6b85048b-bf6f-4451-9a2b-3b55fdb80b86")
        )

    def test_uuid_hex_compact_accepted(self):
        self.assertTrue(
            qr_scanner._looks_like_scanner_token("6b85048bbf6f44519a2b3b55fdb80b86")
        )

    def test_too_short_local_rejected(self):
        self.assertFalse(qr_scanner._looks_like_scanner_token("abc"))

    def test_wrong_length_alphanumeric_rejected(self):
        self.assertFalse(qr_scanner._looks_like_scanner_token("notauuid123456789012"))

    def test_reisa_pin_six_digits_accepted(self):
        self.assertTrue(qr_scanner._looks_like_scanner_token("316229"))

    def test_reisa_pin_four_digits_accepted(self):
        self.assertTrue(qr_scanner._looks_like_scanner_token("1234"))

    def test_digit_pin_too_long_rejected(self):
        self.assertFalse(qr_scanner._looks_like_scanner_token("1234567890123"))

    def test_digit_pin_too_short_rejected(self):
        self.assertFalse(qr_scanner._looks_like_scanner_token("123"))


class UsbFragmentMergeTests(unittest.TestCase):
    def tearDown(self):
        qr_scanner._clear_fragment_buffers()

    def test_uuid_tail_then_leading_hex_fragment_merges(self):
        qr_scanner._clear_fragment_buffers()
        self.assertIsNone(qr_scanner._prepare_decoded_line("b5c794b-9d5c-466f-9e14-335ccf8066a7"))
        merged = qr_scanner._prepare_decoded_line("f")
        self.assertEqual(merged, "fb5c794b-9d5c-466f-9e14-335ccf8066a7")

    def test_leading_orphan_then_hyphen_line_merges(self):
        qr_scanner._clear_fragment_buffers()
        self.assertIsNone(qr_scanner._prepare_decoded_line("f"))
        out = qr_scanner._prepare_decoded_line("b5c794b-9d5c-466f-9e14-335ccf8066a7")
        self.assertEqual(out, "fb5c794b-9d5c-466f-9e14-335ccf8066a7")


class RecentUuidPrefixRecoveryTests(unittest.TestCase):
    def setUp(self):
        self._old_full = qr_scanner._RECENT_FULL_UUID
        self._old_mono = qr_scanner._RECENT_FULL_UUID_MONO

    def tearDown(self):
        qr_scanner._RECENT_FULL_UUID = self._old_full
        qr_scanner._RECENT_FULL_UUID_MONO = self._old_mono

    def test_recover_when_scan_matches_recent_suffix(self):
        import time as time_mod

        full = "fb5c794b-9d5c-466f-9e14-335ccf8066a7"
        qr_scanner._RECENT_FULL_UUID = full
        qr_scanner._RECENT_FULL_UUID_MONO = time_mod.monotonic()
        self.assertEqual(
            qr_scanner._recover_from_recent_leading_byte_loss("5c794b-9d5c-466f-9e14-335ccf8066a7"),
            full,
        )
        self.assertEqual(
            qr_scanner._recover_from_recent_leading_byte_loss("b5c794b-9d5c-466f-9e14-335ccf8066a7"),
            full,
        )

    def test_valid_uuid_does_not_use_recent_branch(self):
        qr_scanner._RECENT_FULL_UUID = "00000000-0000-4000-8000-000000000001"
        qr_scanner._RECENT_FULL_UUID_MONO = __import__("time").monotonic()
        self.assertIsNone(
            qr_scanner._recover_from_recent_leading_byte_loss("fb5c794b-9d5c-466f-9e14-335ccf8066a7")
        )

    def test_no_recent_returns_none(self):
        qr_scanner._RECENT_FULL_UUID = None
        self.assertIsNone(
            qr_scanner._recover_from_recent_leading_byte_loss("5c794b-9d5c-466f-9e14-335ccf8066a7")
        )


class ReadFullFrameTests(unittest.TestCase):
    @patch.object(qr_scanner, "COALESCE_TRAIL_QUIET_SEC", 0.002)
    @patch.object(qr_scanner, "COALESCE_MAX_EXTRA_SEC", 0.02)
    def test_read_full_frame_pulls_trailing_bytes_from_in_waiting(self):
        class FakeSer:
            def __init__(self):
                self._reads = 0

            def read(self, n):
                self._reads += 1
                if self._reads == 1:
                    return b"ab"
                return b"cd"

            @property
            def in_waiting(self):
                return 2 if self._reads == 1 else 0

        self.assertEqual(qr_scanner._read_full_frame(FakeSer()), b"abcd")


class ScannerSegmentSplitTests(unittest.TestCase):
    def test_split_crlf_two_scans(self):
        raw = b"316229\r\nAB12CD34\r\n"
        parts = qr_scanner._split_scan_segments(raw)
        self.assertEqual(parts, [b"316229", b"AB12CD34"])

    def test_split_inter_byte_single_no_newline(self):
        raw = b"316229"
        parts = qr_scanner._split_scan_segments(raw)
        self.assertEqual(parts, [b"316229"])


if __name__ == "__main__":
    unittest.main()
