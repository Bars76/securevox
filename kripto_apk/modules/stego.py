"""modules/stego.py - Steganografi Gambar LSB pada PNG (logika murni, tanpa PySide6).

- Pesan dienkripsi AES (AES-GCM via modules.database) DULU, lalu disisipkan
  dengan teknik LSB (1 bit per channel warna R, G, B).
- Header berisi magic bytes 'SVOX' + panjang pesan (4 byte big-endian).
- Input cover harus PNG (JPG ditolak karena kompresi lossus merusak bit LSB).
- Output disimpan sebagai PNG.
- Menghitung PSNR sebagai perbandingan gambar asli vs stego.
"""
from __future__ import annotations

import os
from typing import Tuple

import numpy as np
from PIL import Image

import modules.database as db_mod

MAGIC = b"SVOX"  # penanda awal pesan tersembunyi


def _cek_kapasitas(piksel: int, jumlah_bit: int) -> bool:
    return jumlah_bit <= piksel * 3  # 3 channel warna per piksel


def sisipkan_pesan(
    path_cover: str, pesan: str, kunci: bytes, path_output: str,
    enkripsi_awal: bool = True
) -> Tuple[dict, float]:
    """Sisipkan pesan ke gambar PNG via LSB.

    Args:
        enkripsi_awal: Jika True, pesan dienkripsi AES-GCM dulu sebelum
            disisipkan (mode aman). Jika False, hanya LSB tanpa enkripsi.
    """
    if not path_cover.lower().endswith(".png"):
        raise ValueError("Cover harus berformat PNG (JPG ditolak: kompresi lossy merusak LSB).")
    if not os.path.isfile(path_cover):
        raise FileNotFoundError(f"Gambar cover tidak ditemukan: {path_cover}")

    # Opsional: enkripsi pesan dengan AES-GCM (kunci dari Master Key).
    if enkripsi_awal:
        ciphertext_b64 = db_mod.enkripsi_teks(pesan, kunci)
        payload_bytes = ciphertext_b64.encode("ascii")
    else:
        payload_bytes = pesan.encode("utf-8")

    # Header: magic + panjang payload.
    panjang = len(payload_bytes)
    header = MAGIC + panjang.to_bytes(4, "big")
    payload = header + payload_bytes

    # Bit yang akan disisipkan.
    bit_list = []
    for byte in payload:
        for i in range(7, -1, -1):
            bit_list.append((byte >> i) & 1)
    jumlah_bit = len(bit_list)

    img = Image.open(path_cover).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError("Gambar cover harus RGB 3 channel.")
    piksel = arr.shape[0] * arr.shape[1]
    if not _cek_kapasitas(piksel, jumlah_bit):
        raise ValueError(
            f"Pesan terlalu panjang untuk gambar ini. Butuh {jumlah_bit} bit, "
            f"kapasitas {piksel * 3} bit."
        )

    salin = arr.copy()
    idx = 0
    for y in range(arr.shape[0]):
        for x in range(arr.shape[1]):
            for c in range(3):
                if idx < jumlah_bit:
                    salin[y, x, c] = (salin[y, x, c] & 0xFE) | bit_list[idx]
                    idx += 1
                else:
                    break
            if idx >= jumlah_bit:
                break
        if idx >= jumlah_bit:
            break

    Image.fromarray(salin, "RGB").save(path_output, "PNG")
    psnr = _hitung_psnr(arr, salin)

    info = {
        "cover": path_cover,
        "stego": path_output,
        "pesan_asli": pesan,
        "mode": "AES + LSB" if enkripsi_awal else "LSB saja",
        "bit_disipkan": jumlah_bit,
        "kapasitas_bit": piksel * 3,
    }
    return info, psnr


def ekstrak_pesan(path_stego: str, kunci: bytes, enkripsi_awal: bool = True) -> str:
    """Ekstrak dan dekripsi pesan tersembunyi dari gambar stego PNG.

    Args:
        enkripsi_awal: Jika True, hasil ekstraksi didekripsi AES-GCM.
            Jika False, hasil dikembalikan sebagai teks mentah.
    """
    if not os.path.isfile(path_stego):
        raise FileNotFoundError(f"Gambar stego tidak ditemukan: {path_stego}")

    img = Image.open(path_stego).convert("RGB")
    arr = np.array(img, dtype=np.uint8)

    bit_list = []
    for y in range(arr.shape[0]):
        for x in range(arr.shape[1]):
            for c in range(3):
                bit_list.append(arr[y, x, c] & 1)

    # Ubah bit ke byte. Proses semua byte lengkap (abaikan sisa bit < 8 di akhir).
    bytes_hasil = bytearray()
    lengkap = len(bit_list) // 8 * 8
    for i in range(0, lengkap, 8):
        byte = 0
        for b in bit_list[i : i + 8]:
            byte = (byte << 1) | b
        bytes_hasil.append(byte)

    data = bytes(bytes_hasil)
    # Cari magic bytes.
    if MAGIC not in data:
        raise ValueError("Tidak ada pesan tersembunyi (magic bytes tidak ditemukan).")
    pos = data.index(MAGIC)
    data = data[pos + len(MAGIC) :]
    if len(data) < 4:
        raise ValueError("Header panjang pesan rusak.")
    panjang = int.from_bytes(data[:4], "big")
    payload = data[4 : 4 + panjang]
    if len(payload) < panjang:
        raise ValueError("Data pesan tidak lengkap.")
    if enkripsi_awal:
        ciphertext_b64 = payload.decode("ascii")
        return db_mod.dekripsi_teks(ciphertext_b64, kunci)
    else:
        return payload.decode("utf-8")


def _hitung_psnr(asli: np.ndarray, stego: np.ndarray) -> float:
    mse = np.mean((asli.astype(np.float32) - stego.astype(np.float32)) ** 2)
    if mse == 0:
        return float("inf")
    return 20 * np.log10(255.0 / np.sqrt(mse))


def hitung_psnr(path_cover: str, path_stego: str) -> float:
    """Hitung PSNR antara gambar asli dan stego."""
    a = np.array(Image.open(path_cover).convert("RGB"), dtype=np.uint8)
    b = np.array(Image.open(path_stego).convert("RGB"), dtype=np.uint8)
    return _hitung_psnr(a, b)
