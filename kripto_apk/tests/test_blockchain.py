"""tests/test_blockchain.py - Uji blockchain aset: PoW, validasi, deteksi manipulasi."""
from __future__ import annotations

import os
import unittest

import modules.blockchain as bc


def _reset_chain() -> None:
    if os.path.exists(bc.CHAIN_PATH):
        os.remove(bc.CHAIN_PATH)


class TestBlockchain(unittest.TestCase):
    def test_genesis_dan_pow(self) -> None:
        _reset_chain()
        rantai = bc.Blockchain()
        self.assertEqual(len(rantai.chain), 1)
        self.assertEqual(rantai.chain[0]["index"], 0)
        self.assertTrue(rantai.chain[0]["hash"].startswith("000"))  # PoW genesis

    def test_tambah_aset_dan_validasi(self) -> None:
        _reset_chain()
        rantai = bc.Blockchain()
        with open("data/asset_uji.txt", "w") as f:
            f.write("konten aset uji")
        blok = rantai.tambah_aset("Aset Uji", "data/asset_uji.txt", "admin")
        self.assertTrue(blok["hash"].startswith("000"))
        valid, rusak = rantai.validasi_chain()
        self.assertTrue(valid)
        self.assertIsNone(rusak)

    def test_deteksi_manipulasi(self) -> None:
        _reset_chain()
        rantai = bc.Blockchain()
        with open("data/asset_uji2.txt", "w") as f:
            f.write("konten aset uji 2")
        rantai.tambah_aset("Aset Uji 2", "data/asset_uji2.txt", "admin")
        rantai.simulasi_manipulasi(
            1,
            {
                "asset_name": "Aset Uji 2",
                "file_hash": "DIUBAH",
                "owner": "admin",
                "file_path": "data/asset_uji2.txt",
            },
        )
        valid, rusak = rantai.validasi_chain()
        self.assertFalse(valid)
        self.assertEqual(rusak, 1)
