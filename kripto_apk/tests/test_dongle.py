"""tests/test_dongle.py - Uji deteksi dongle (bentuk boolean, skip jika tidak ada USB)."""
from __future__ import annotations

import unittest

import modules.dongle as dongle


class TestDongle(unittest.TestCase):
    def test_cek_dongle_bentuk_boolean(self) -> None:
        """cek_dongle selalu mengembalikan bool."""
        self.assertIsInstance(dongle.cek_dongle(), bool)
