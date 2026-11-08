"""tests/test_stego.py - Uji steganografi LSB PNG: decrypt(extract(embed(x))) == x."""
from __future__ import annotations

import os
import unittest

import numpy as np
from PIL import Image

import modules.stego as stego

KUNCI = b"0123456789abcdef0123456789abcdef"


def _buat_png(path: str, ukuran=(60, 60)) -> None:
    arr = np.random.randint(0, 255, (*ukuran, 3), dtype=np.uint8)
    Image.fromarray(arr, "RGB").save(path, "PNG")


class TestStego(unittest.TestCase):
    def test_stego_roundtrip(self) -> None:
        cover = "data/stego/test_cover.png"
        stego_path = "data/stego/test_stego.png"
        _buat_png(cover)
        pesan = "pesan steganografi rahasia untuk uji coba"
        info, psnr = stego.sisipkan_pesan(cover, pesan, KUNCI, stego_path)
        self.assertLessEqual(info["bit_disipkan"], info["kapasitas_bit"])
        ekstraksi = stego.ekstrak_pesan(stego_path, KUNCI)
        self.assertEqual(ekstraksi, pesan)
        self.assertGreater(psnr, 40)  # gambar stego tampak sama dengan asli

    def test_jpg_ditolak(self) -> None:
        cover = "data/stego/test_cover.jpg"
        arr = np.random.randint(0, 255, (60, 60, 3), dtype=np.uint8)
        Image.fromarray(arr, "RGB").save(cover, "JPEG")
        with self.assertRaises(ValueError):
            stego.sisipkan_pesan(cover, "pesan", KUNCI, "data/stego/x.png")

    def test_stego_lsb_saja_roundtrip(self) -> None:
        """Mode LSB saja (tanpa enkripsi AES): ekstraksi harus mengembalikan teks asli."""
        cover = "data/stego/test_cover_lsb.png"
        stego_path = "data/stego/test_stego_lsb.png"
        _buat_png(cover)
        pesan = "teks murni tanpa enkripsi AES"
        info, psnr = stego.sisipkan_pesan(
            cover, pesan, KUNCI, stego_path, enkripsi_awal=False
        )
        self.assertEqual(info["mode"], "LSB saja")
        ekstraksi = stego.ekstrak_pesan(stego_path, KUNCI, enkripsi_awal=False)
        self.assertEqual(ekstraksi, pesan)
        self.assertGreater(psnr, 40)
