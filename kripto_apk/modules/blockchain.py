"""modules/blockchain.py - Blockchain Sederhana untuk Aset (logika murni, tanpa PySide6).

Struktur blok:
    index, timestamp, data (nama aset, SHA-256 file aset, pemilik),
    previous_hash, nonce, hash

Proof of Work ringan: hash blok harus diawali "000".
Blok genesis dibuat otomatis.
Chain disimpan di data/chain.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Optional

CHAIN_PATH = "data/chain.json"
DIFFICULTY = "000"  # hash blok harus diawali 3 nol


def _hash_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: str) -> str:
    """SHA-256 isi file aset."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blok in iter(lambda: f.read(65536), b""):
            h.update(blok)
    return h.hexdigest()


def _hash_blok(blok: dict) -> str:
    """Hash blok dari seluruh field kecuali 'hash' itu sendiri."""
    salinan = {k: v for k, v in blok.items() if k != "hash"}
    urutan = json.dumps(salinan, sort_keys=True, separators=(",", ":")).encode()
    return _hash_sha256(urutan)


def _buat_genesis() -> dict:
    blok = {
        "index": 0,
        "timestamp": time.time(),
        "data": {"asset_name": "genesis", "file_hash": "", "owner": "sistem", "file_path": ""},
        "previous_hash": "0" * 64,
        "nonce": 0,
    }
    blok["nonce"] = _proof_of_work_static(blok)
    blok["hash"] = _hash_blok(blok)
    return blok


def _proof_of_work_static(blok: dict) -> int:
    nonce = 0
    while True:
        blok["nonce"] = nonce
        h = _hash_blok(blok)
        if h.startswith(DIFFICULTY):
            return nonce
        nonce += 1


class Blockchain:
    def __init__(self) -> None:
        self.chain: list[dict] = []
        self._muat()

    def _muat(self) -> None:
        if os.path.isfile(CHAIN_PATH):
            try:
                with open(CHAIN_PATH, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    self.chain = data
                    return
            except (OSError, json.JSONDecodeError):
                pass
        self.chain = [_buat_genesis()]
        self._simpan()

    def _simpan(self) -> None:
        os.makedirs("data", exist_ok=True)
        with open(CHAIN_PATH, "w", encoding="utf-8") as f:
            json.dump(self.chain, f, indent=2, ensure_ascii=False)

    def _proof_of_work(self, blok: dict) -> int:
        nonce = 0
        while True:
            blok["nonce"] = nonce
            h = _hash_blok(blok)
            if h.startswith(DIFFICULTY):
                return nonce
            nonce += 1

    def tambah_aset(
        self, nama_aset: str, path_file: str, pemilik: str
    ) -> dict:
        """Tambah aset: hitung SHA-256 file, buat blok, PoW, simpan chain."""
        if not os.path.isfile(path_file):
            raise FileNotFoundError(f"File aset tidak ditemukan: {path_file}")
        file_hash = _hash_file(path_file)
        data = {
            "asset_name": nama_aset,
            "file_hash": file_hash,
            "owner": pemilik,
            "file_path": path_file,
        }
        blok_baru = {
            "index": len(self.chain),
            "timestamp": time.time(),
            "data": data,
            "previous_hash": self.chain[-1]["hash"],
            "nonce": 0,
        }
        blok_baru["nonce"] = self._proof_of_work(blok_baru)
        blok_baru["hash"] = _hash_blok(blok_baru)
        self.chain.append(blok_baru)
        self._simpan()
        return blok_baru

    def lihat_chain(self) -> list[dict]:
        return list(self.chain)

    def validasi_chain(self) -> tuple[bool, Optional[int]]:
        """
        Validasi seluruh rantai.
        Mengembalikan (valid, index_blok_rusak_atau_None).
        """
        if not self.chain:
            return False, None
        # Cek genesis.
        if self.chain[0]["index"] != 0 or self.chain[0]["previous_hash"] != "0" * 64:
            return False, 0
        for i in range(1, len(self.chain)):
            now = self.chain[i]
            before = self.chain[i - 1]
            # Hash blok saat ini harus valid & memenuhi difficulty.
            if _hash_blok(now) != now["hash"]:
                return False, i
            if not now["hash"].startswith(DIFFICULTY):
                return False, i
            if now["previous_hash"] != before["hash"]:
                return False, i
            if now["index"] != before["index"] + 1:
                return False, i
        return True, None

    def verifikasi_aset(self, nama_aset: str) -> tuple[bool, str, Optional[str]]:
        """
        Verifikasi file aset: cari blok dengan nama_aset, bandingkan hash file
        sekarang dengan hash yang tersimpan di blok.
        Mengembalikan (cocok, pesan, index_blok).
        """
        for blok in self.chain:
            data = blok.get("data", {})
            if data.get("asset_name") == nama_aset:
                path_file = data.get("file_path")
                hash_simpan = data.get("file_hash", "")
                if path_file and os.path.isfile(path_file):
                    hash_sekarang = _hash_file(path_file)
                    cocok = hash_sekarang == hash_simpan
                    return (
                        cocok,
                        f"Blok {blok['index']}: hash simpan {hash_simpan[:12]}... "
                        f"{'COCOK' if cocok else 'TIDAK COCOK'} (file sekarang {hash_sekarang[:12]}...)",
                        int(blok["index"]),
                    )
                return False, f"Blok {blok['index']}: file aset tidak ditemukan di {path_file}", int(
                    blok["index"]
                )
        return False, f"Aset '{nama_aset}' tidak ditemukan di rantai.", None

    def simulasi_manipulasi(self, index: int, data_baru: dict) -> bool:
        """Ubah data suatu blok untuk UJI deteksi manipulasi (demo)."""
        if index < 0 or index >= len(self.chain):
            return False
        self.chain[index]["data"] = data_baru
        # Hash blok tidak diupdate lagi -> akan terdeteksi rusak saat validasi.
        self._simpan()
        return True
