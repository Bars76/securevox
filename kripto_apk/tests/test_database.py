"""tests/test_database.py - Uji AES-GCM database: field sensitif terenkripsi."""
from __future__ import annotations

import unittest

import modules.database as db

KUNCI = b"0123456789abcdef0123456789abcdef"


class TestDatabase(unittest.TestCase):
    def test_aes_gcm_roundtrip(self) -> None:
        plain = "data sensitif rahasia"
        enkripsi = db.enkripsi_teks(plain, KUNCI)
        dekripsi = db.dekripsi_teks(enkripsi, KUNCI)
        self.assertEqual(dekripsi, plain)
        self.assertNotEqual(enkripsi, plain)  # ciphertext bukan plaintext

    def test_database_simpan_baca(self) -> None:
        database = db.Database()
        database.set_master_key(KUNCI)
        ok, pesan = database.add_message("admin", "pesan rahasia database")
        self.assertTrue(ok)
        rows = database.get_messages()
        self.assertGreaterEqual(len(rows), 1)
        ct = rows[0]["content_enc"]
        self.assertNotEqual(ct, "pesan rahasia database")  # disimpan ciphertext
        self.assertEqual(database.dekripsi_message(ct), "pesan rahasia database")
