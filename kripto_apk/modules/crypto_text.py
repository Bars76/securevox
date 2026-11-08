"""modules/crypto_text.py - Enkripsi Teks (logika murni, tanpa PySide6).

Urutan enkripsi (2 lapis):
    1. Vigenère Cipher (kunci yang diinput pengguna)
    2. AES-256-CBC (kunci yang diinput pengguna, manual)

Dekripsi dilakukan dengan urutan terbalik: AES → Vigenère.
"""
from __future__ import annotations

import base64
from typing import Tuple

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

BLOCK_SIZE = 16  # AES block size (byte)


# ------------------------------------------------------------------ padding
def _pad(data: bytes) -> bytes:
    pad_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([pad_len]) * pad_len


def _unpad(data: bytes) -> bytes:
    pad_len = data[-1]
    if pad_len < 1 or pad_len > BLOCK_SIZE:
        raise ValueError("Padding tidak valid (ciphertext rusak atau kunci salah).")
    return data[:-pad_len]


# ---------------------------------------------------------------- Vigenère
def vigenere_enkripsi(plaintext: str, kunci: str) -> str:
    """Vigenère: C_i = (P_i + K_i) mod 26 untuk huruf.

    Karakter non-alphabet dipertahankan pada posisi tempatnya; case huruf
    juga dipertahankan. Indeks kunci hanya bertambah pada huruf alfabet.
    """
    kunci = kunci.upper()
    if not kunci or not kunci.isalpha():
        raise ValueError("Kunci Vigenère harus berupa huruf alfabet (A-Z).")
    k_len = len(kunci)
    k_idx = 0
    hasil: list[str] = []
    for c in plaintext:
        if c.isalpha():
            base = ord("A") if c.isupper() else ord("a")
            p = ord(c) - base
            k = ord(kunci[k_idx % k_len]) - ord("A")
            hasil.append(chr(((p + k) % 26) + base))
            k_idx += 1
        else:
            hasil.append(c)
    return "".join(hasil)


def vigenere_dekripsi(ciphertext: str, kunci: str) -> str:
    """Vigenère: P_i = (C_i - K_i) mod 26 untuk huruf."""
    kunci = kunci.upper()
    if not kunci or not kunci.isalpha():
        raise ValueError("Kunci Vigenère harus berupa huruf alfabet (A-Z).")
    k_len = len(kunci)
    k_idx = 0
    hasil: list[str] = []
    for c in ciphertext:
        if c.isalpha():
            base = ord("A") if c.isupper() else ord("a")
            c_val = ord(c) - base
            k = ord(kunci[k_idx % k_len]) - ord("A")
            hasil.append(chr(((c_val - k) % 26) + base))
            k_idx += 1
        else:
            hasil.append(c)
    return "".join(hasil)


# ---------------------------------------------------------------- AES-256-CBC
def _kunci_aes_dari_string(kunci_teks: str) -> bytes:
    """Ubah kunci teks menjadi 32 byte (AES-256) via SHA-256 hash."""
    from Crypto.Hash import SHA256
    return SHA256.new(kunci_teks.encode("utf-8")).digest()


def aes_enkripsi(plaintext: str, kunci_teks: str) -> str:
    """AES-256-CBC: kunci di-hash SHA-256 menjadi 32 byte, IV acak 16 byte,
    PKCS7 padding, Base64(IV + ciphertext)."""
    kunci = _kunci_aes_dari_string(kunci_teks)
    iv = get_random_bytes(16)
    cipher = AES.new(kunci, AES.MODE_CBC, iv=iv)
    ciphertext = cipher.encrypt(_pad(plaintext.encode("utf-8")))
    return base64.b64encode(iv + ciphertext).decode("ascii")


def aes_dekripsi(ciphertext_b64: str, kunci_teks: str) -> str:
    kunci = _kunci_aes_dari_string(kunci_teks)
    data = base64.b64decode(ciphertext_b64)
    if len(data) < 16 + 16:
        raise ValueError("Payload ciphertext terlalu pendek / rusak.")
    iv = data[:16]
    ct = data[16:]
    cipher = AES.new(kunci, AES.MODE_CBC, iv=iv)
    plaintext = _unpad(cipher.decrypt(ct))
    return plaintext.decode("utf-8")


# ----------------------------------------------------------------- Enkripsi 2 Lapisan
class EnkripsiHasil:
    """Hasil tiap tahap enkripsi untuk ditampilkan di UI."""

    def __init__(
        self,
        plaintext: str,
        setelah_vigenere: str,
        ciphertext_akhir: str,
    ) -> None:
        self.plaintext = plaintext
        self.setelah_vigenere = setelah_vigenere
        self.ciphertext_akhir = ciphertext_akhir


def enkripsi_dua_lapisan(
    plaintext: str,
    kunci_vigenere: str,
    kunci_aes: str,
) -> EnkripsiHasil:
    """Enkripsi 2 lapis: Vigenère -> AES-256."""
    tahap1 = vigenere_enkripsi(plaintext, kunci_vigenere)
    tahap2 = aes_enkripsi(tahap1, kunci_aes)
    return EnkripsiHasil(plaintext, tahap1, tahap2)


def dekripsi_dua_lapisan(
    ciphertext_b64: str,
    kunci_vigenere: str,
    kunci_aes: str,
) -> str:
    """Dekripsi 2 lapis (urutan terbalik): AES-256 -> Vigenère."""
    tahap2 = aes_dekripsi(ciphertext_b64, kunci_aes)
    tahap1 = vigenere_dekripsi(tahap2, kunci_vigenere)
    return tahap1
