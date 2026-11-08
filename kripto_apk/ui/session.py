"""Session: menyimpan Master Key dan user aktif hanya di memori (RAM).

Master Key tidak pernah ditulis ke disk. Hapus dengan clear() saat logout
atau saat dongle dicabut sehingga kunci hilang dari memori.
"""
from __future__ import annotations

from typing import Optional


class Session:
    def __init__(self) -> None:
        self.master_key: Optional[bytes] = None
        self.username: Optional[str] = None
        self.user_id: Optional[int] = None

    def set_user(self, user_id: int, username: str, master_key: bytes) -> None:
        self.user_id = user_id
        self.username = username
        self.master_key = master_key

    def clear(self) -> None:
        self.master_key = None
        self.username = None
        self.user_id = None

    @property
    def is_authenticated(self) -> bool:
        return self.master_key is not None and self.username is not None


# Sesi tunggal yang digunakan seluruh aplikasi.
session = Session()
