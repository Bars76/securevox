"""modules/database.py - Database SQLite SecureVox (logika murni, tanpa PySide6).

Tabel:
    users        - id, username, salt, password_hash, created_at
    messages     - id, sender, content_enc, created_at
    audio_messages - id, sender, file_path, nonce, size, created_at
    stego_messages - id, sender, image_path, created_at
    logs         - id, event, status, created_at

Konten pesan dan field sensitif disimpan sebagai ciphertext AES-GCM
(nonce + tag + ciphertext, Base64) dengan kunci dari Master Key.
"""
from __future__ import annotations

import base64
import os
import sqlite3
import time
from typing import Optional

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

DB_PATH = "data/securevox.db"

GCM_NONCE_SIZE = 12
GCM_TAG_SIZE = 16


def _koneksi() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Buat tabel jika belum ada."""
    conn = _koneksi()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            content_enc TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS file_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            file_path TEXT NOT NULL,
            nonce TEXT NOT NULL,
            size INTEGER NOT NULL,
            deskripsi TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    # Migrasi: tambahkan kolom deskripsi jika tabel sudah ada tanpa kolom itu.
    cols = [r[1] for r in conn.execute("PRAGMA table_info(file_messages)").fetchall()]
    if "deskripsi" not in cols:
        conn.execute("ALTER TABLE file_messages ADD COLUMN deskripsi TEXT")
    conn.commit()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS stego_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            image_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def _sekarang() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ----------------------------------------------------------------- AES-GCM
def enkripsi_teks(teks: str, kunci: bytes) -> str:
    """Enkripsi teks dengan AES-256-GCM. Hasil: Base64(nonce + tag + ciphertext)."""
    nonce = get_random_bytes(GCM_NONCE_SIZE)
    cipher = AES.new(kunci, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(teks.encode("utf-8"))
    payload = nonce + tag + ciphertext
    return base64.b64encode(payload).decode("ascii")


def dekripsi_teks(payload_b64: str, kunci: bytes) -> str:
    """Dekripsi ciphertext AES-GCM (Base64) kembali ke teks asli."""
    data = base64.b64decode(payload_b64)
    if len(data) < GCM_NONCE_SIZE + GCM_TAG_SIZE:
        raise ValueError("Payload ciphertext terlalu pendek / rusak.")
    nonce = data[:GCM_NONCE_SIZE]
    tag = data[GCM_NONCE_SIZE : GCM_NONCE_SIZE + GCM_TAG_SIZE]
    ciphertext = data[GCM_NONCE_SIZE + GCM_TAG_SIZE :]
    cipher = AES.new(kunci, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return plaintext.decode("utf-8")


# ----------------------------------------------------------------- Database
class Database:
    def __init__(self, master_key: Optional[bytes] = None) -> None:
        self.master_key = master_key
        init_db()

    def set_master_key(self, kunci: bytes) -> None:
        self.master_key = kunci

    # --------------------------------------------------------------- users
    def register_user(self, username: str, password: str) -> tuple[bool, str]:
        """Daftar akun baru. Simpan salt + SHA-256(salt+password)."""
        if not username or not password:
            return False, "Username dan password tidak boleh kosong."
        if self.get_user(username) is not None:
            return False, "Username sudah terdaftar."
        salt = os.urandom(16).hex()
        password_hash = _hash_password(password, salt)
        try:
            conn = _koneksi()
            conn.execute(
                "INSERT INTO users (username, salt, password_hash, created_at) "
                "VALUES (?, ?, ?, ?)",
                (username, salt, password_hash, _sekarang()),
            )
            conn.commit()
            conn.close()
            return True, "Akun berhasil didaftarkan."
        except sqlite3.Error as exc:
            return False, f"Gagal mendaftar: {exc}"

    def get_user(self, username: str) -> Optional[sqlite3.Row]:
        conn = _koneksi()
        row = conn.execute(
            "SELECT id, username, salt, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()
        return row

    def verify_user(self, username: str, password: str) -> Optional[int]:
        """Verifikasi login. Mengembalikan user_id jika berhasil, None jika gagal."""
        row = self.get_user(username)
        if row is None:
            return None
        if not _verify_password(password, row["salt"], row["password_hash"]):
            return None
        return int(row["id"])

    # ------------------------------------------------------------ messages
    def add_message(self, sender: str, plaintext: str) -> tuple[bool, str]:
        """Simpan pesan teks sebagai ciphertext AES-GCM."""
        if self.master_key is None:
            return False, "Master Key belum tersedia (belum login)."
        try:
            content_enc = enkripsi_teks(plaintext, self.master_key)
            conn = _koneksi()
            conn.execute(
                "INSERT INTO messages (sender, content_enc, created_at) "
                "VALUES (?, ?, ?)",
                (sender, content_enc, _sekarang()),
            )
            conn.commit()
            conn.close()
            return True, "Pesan tersimpan."
        except Exception as exc:  # noqa: BLE001
            return False, f"Gagal menyimpan pesan: {exc}"

    def get_messages(self, limit: int = 50) -> list[dict]:
        """Ambil pesan (content masih dalam bentuk ciphertext/Base64)."""
        conn = _koneksi()
        rows = conn.execute(
            "SELECT id, sender, content_enc, created_at FROM messages "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def dekripsi_message(self, content_enc: str) -> str:
        """Dekripsi isi pesan dengan Master Key (untuk ditampilkan di UI)."""
        if self.master_key is None:
            raise RuntimeError("Master Key belum tersedia.")
        return dekripsi_teks(content_enc, self.master_key)

    # ------------------------------------------------------------ file
    def add_file_message(
        self, sender: str, file_path: str, nonce_hex: str, size: int,
        deskripsi: str = ""
    ) -> int:
        """Simpan metadata file terenkripsi (PDF atau lain). Mengembalikan id baris."""
        conn = _koneksi()
        cur = conn.execute(
            "INSERT INTO file_messages (sender, file_path, nonce, size, deskripsi, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sender, file_path, nonce_hex, size, deskripsi, _sekarang()),
        )
        conn.commit()
        id_baris = int(cur.lastrowid)
        conn.close()
        return id_baris

    def get_file_messages(self, limit: int = 50) -> list[dict]:
        conn = _koneksi()
        rows = conn.execute(
            "SELECT id, sender, file_path, nonce, size, deskripsi, created_at FROM file_messages "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ---------------------------------------------------------------- logs
    def add_log(self, event: str, status: str) -> None:
        try:
            conn = _koneksi()
            conn.execute(
                "INSERT INTO logs (event, status, created_at) VALUES (?, ?, ?)",
                (event, status, _sekarang()),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

    def get_logs(self, limit: int = 100) -> list[dict]:
        conn = _koneksi()
        rows = conn.execute(
            "SELECT id, event, status, created_at FROM logs "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------- DB mentah
    def get_raw_messages(self) -> list[dict]:
        """Lihat isi DB mentah (ciphertext) untuk demonstrasi demo."""
        conn = _koneksi()
        rows = conn.execute(
            "SELECT id, sender, content_enc, created_at FROM messages "
            "ORDER BY id DESC LIMIT 50"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


# ------------------------------------------------------------------- hashing
def _hash_password(password: str, salt: str) -> str:
    import hashlib

    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
    import hashlib
    import hmac

    hitung = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(hitung, stored_hash)
