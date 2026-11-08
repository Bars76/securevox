"""tests/test_crypto_text.py - Uji enkripsi teks 2 lapis (decrypt(encrypt(x)) == x)."""
from __future__ import annotations

import unittest

import modules.crypto_text as ct


class TestCryptoText(unittest.TestCase):
    def test_enkripsi_dua_lapisan_roundtrip(self) -> None:
        plain = "Ini adalah pesan rahasia SecureVox 123! @#$"
        hasil = ct.enkripsi_dua_lapisan(plain, "KUNCIRAHASIA", "kunci_aes_manual")
        dekripsi = ct.dekripsi_dua_lapisan(
            hasil.ciphertext_akhir, "KUNCIRAHASIA", "kunci_aes_manual"
        )
        self.assertEqual(dekripsi, plain)

    def test_tiap_tahap_tercatat(self) -> None:
        """UI wajib menampilkan hasil setiap tahap (plaintext, Vigenère, AES)."""
        hasil = ct.enkripsi_dua_lapisan("HaloDunia", "KUNCI", "kunci_aes")
        self.assertEqual(hasil.plaintext, "HaloDunia")
        self.assertNotEqual(hasil.setelah_vigenere, "")
        self.assertNotEqual(hasil.ciphertext_akhir, "")
        self.assertNotEqual(hasil.ciphertext_akhir, hasil.plaintext)
