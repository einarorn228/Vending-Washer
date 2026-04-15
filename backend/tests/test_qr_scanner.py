"""Unit tests for QR scanner ingress validation."""

import unittest

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


if __name__ == "__main__":
    unittest.main()
