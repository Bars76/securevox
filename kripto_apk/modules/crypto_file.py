"""modules/crypto_file.py - Enkripsi File (PDF dan lain-lain) dengan ChaCha20
(logika murni, tanpa PySide6).

- Pilih file PDF (atau file apa pun).
- Enkripsi seluruh byte file dengan ChaCha20 (algoritma berbeda dari teks),
  nonce acak disimpan di awal file terenkripsi (.enc) dan di database.
- Output: file .enc di data/files/, metadata di database.
- Dekripsi: kembalikan byte asli, simpan sebagai file asli (mis. .pdf).
"""
from __future__ import annotations

import os
from typing import Tuple

from Crypto.Cipher import ChaCha20
from Crypto.Random import get_random_bytes

FILES_DIR = "data/files"
CHACHA20_NONCE = 12  # ukuran nonce ChaCha20 (byte)
CHACHA20_KEY = 32  # kunci ChaCha20 256-bit (byte)

os.makedirs(FILES_DIR, exist_ok=True)


def enkripsi_file(
    path_file: str, kunci: bytes
) -> Tuple[str, bytes, int, int, str]:
    """Enkripsi seluruh byte file (PDF atau lain) dengan ChaCha20.

    Mengembalikan (path_enc, nonce, size_asli, size_enkripsi, ekstensi_asli).
    File .enc = nonce (12 byte) + ciphertext.
    """
    if len(kunci) != CHACHA20_KEY:
        raise ValueError("Kunci ChaCha20 harus 32 byte (256-bit).")

    if not os.path.isfile(path_file):
        raise FileNotFoundError(f"File tidak ditemukan: {path_file}")

    with open(path_file, "rb") as f:
        data_asli = f.read()
    size_asli = len(data_asli)
    ekstensi_asli = os.path.splitext(path_file)[1].lower() or ".file"

    nonce = get_random_bytes(CHACHA20_NONCE)
    cipher = ChaCha20.new(key=kunci, nonce=nonce)
    ciphertext = cipher.encrypt(data_asli)

    nama_enc = os.path.basename(path_file) + ".enc"
    path_enc = os.path.join(FILES_DIR, nama_enc)
    with open(path_enc, "wb") as f:
        f.write(nonce + ciphertext)

    size_enkripsi = os.path.getsize(path_enc)
    return path_enc, nonce, size_asli, size_enkripsi, ekstensi_asli


def dekripsi_file(path_enc: str, kunci: bytes) -> Tuple[bytes, str]:
    """Dekripsi file .enc kembali ke byte asli.

    Mengembalikan (data_asli, ekstensi_asli).
    Ekstensi asli dibaca dari nama file .enc (mis. 'dokumen.pdf.enc' -> '.pdf').
    """
    if len(kunci) != CHACHA20_KEY:
        raise ValueError("Kunci ChaCha20 harus 32 byte (256-bit).")

    if not os.path.isfile(path_enc):
        raise FileNotFoundError(f"File terenkripsi tidak ditemukan: {path_enc}")

    with open(path_enc, "rb") as f:
        isi = f.read()
    if len(isi) < CHACHA20_NONCE:
        raise ValueError("File .enc rusak (terlalu pendek untuk nonce).")

    nonce = isi[:CHACHA20_NONCE]
    ciphertext = isi[CHACHA20_NONCE:]
    cipher = ChaCha20.new(key=kunci, nonce=nonce)
    data_asli = cipher.decrypt(ciphertext)

    # Ekstrak ekstensi asli dari nama file: 'nama.pdf.enc' -> '.pdf'
    nama_file = os.path.basename(path_enc)
    if nama_file.endswith(".enc"):
        nama_dengan_ext = nama_file[:-4]  # hapus .enc
        if "." in nama_dengan_ext:
            ekstensi_asli = "." + nama_dengan_ext.split(".")[-1]
        else:
            ekstensi_asli = ".file"
    else:
        ekstensi_asli = ".file"

    return data_asli, ekstensi_asli


def info_ciphertext_hex(path_enc: str, panjang: int = 32) -> str:
    """Ambil potongan hex ciphertext (untuk ditampilkan di UI)."""
    with open(path_enc, "rb") as f:
        isi = f.read()
    body = isi[CHACHA20_NONCE:]  # skip nonce
    return body[:panjang].hex()
