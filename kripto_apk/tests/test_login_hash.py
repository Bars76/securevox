"""tests/test_login_hash.py - Uji hash password (SHA-256 + salt, waktu konstan)."""
from __future__ import annotations

import unittest

import modules.login as lg


class TestLoginHash(unittest.TestCase):
    def test_hash_roundtrip(self) -> None:
        hashed, salt = lg.hash_password("rahasia123")
        self.assertTrue(lg.verify_password("rahasia123", salt, hashed))
        self.assertFalse(lg.verify_password("salah", salt, hashed))

    def test_hash_beda_setiap_kali(self) -> None:
        h1, s1 = lg.hash_password("sama")
        h2, s2 = lg.hash_password("sama")
        self.assertNotEqual(s1, s2)  # salt acak per user
        self.assertNotEqual(h1, h2)
