"""modules/login.py - Registrasi dan login SecureVox (logika murni, tanpa PySide6).

- Registrasi: username + password, password di-hash SHA-256(salt + password)
  dengan salt acak 16 byte per user. Hanya salt dan hash yang disimpan.
- Login: membandingkan hash dengan hmac.compare_digest (waktu konstan).
- Setelah login berhasil, turunkan Master Key:

    Master Key = PBKDF2(password + isi_securevox.key, salt_master,
                        200.000 iterasi, 32 byte)

  Master Key hanya ada di memori (Session) selama sesi.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Optional

from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2

import modules.database as database
import modules.dongle as dongle

CONFIG_PATH = "config.json"
MASTER_SALT_HEX_KEY = "master_salt"
PBKDF2_ITERASI = 200_000
MASTER_KEY_PANJANG = 32


def _load_config() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _simpan_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def load_or_create_master_salt() -> bytes:
    """Ambil salt_master dari config.json, generate jika belum ada."""
    cfg = _load_config()
    hex_salt = cfg.get(MASTER_SALT_HEX_KEY)
    if hex_salt:
        try:
            return bytes.fromhex(hex_salt)
        except ValueError:
            pass
    salt_baru = os.urandom(16)
    cfg[MASTER_SALT_HEX_KEY] = salt_baru.hex()
    _simpan_config(cfg)
    return salt_baru


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """SHA-256(salt + password). Mengembalikan (hash_hex, salt_hex)."""
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hashed, salt


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    """Perbandingan waktu konstan."""
    hitung = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(hitung, stored_hash)


def derive_master_key(
    password: str, key_file: bytes, salt_master: bytes
) -> bytes:
    """Master Key = PBKDF2(password + isi_securevox.key, salt_master, 200k, 32 byte)."""
    material = password.encode("utf-8") + key_file
    return PBKDF2(
        material,
        salt_master,
        dkLen=MASTER_KEY_PANJANG,
        count=PBKDF2_ITERASI,
        hmac_hash_module=SHA256,
    )


def register_user(username: str, password: str) -> tuple[bool, str]:
    """Daftar akun baru melalui database."""
    return database.Database().register_user(username, password)


def login(
    username: str, password: str
) -> tuple[bool, str, Optional[int], Optional[bytes]]:
    """
    Proses login lengkap.

    Mengembalikan:
        (sukses, pesan, user_id, master_key_atau_None)
    """
    if not username or not password:
        return False, "Username dan password tidak boleh kosong.", None, None

    # Dongle harus terpasang agar login bisa dilakukan.
    if not dongle.cek_dongle():
        return False, "Dongle tidak terdeteksi. Colokkan dongle dulu.", None, None

    db = database.Database()
    user_id = db.verify_user(username, password)
    if user_id is None:
        db.add_log(f"Login gagal: {username}", "gagal")
        return False, "Username atau password salah.", None, None

    # Baca file kunci dari dongle dan turunkan Master Key.
    key_file = dongle.baca_file_kunci()
    if key_file is None:
        return False, "File kunci dongle tidak terbaca.", None, None

    salt_master = load_or_create_master_salt()
    master_key = derive_master_key(password, key_file, salt_master)

    db.set_master_key(master_key)
    db.add_log(f"Login berhasil: {username}", "berhasil")

    return True, "Login berhasil.", user_id, master_key
