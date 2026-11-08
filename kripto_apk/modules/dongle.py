"""modules/dongle.py - Deteksi USB dongle SecureVox (logika murni, tanpa PySide6).

Dongle dianggap SAH hanya jika keduanya terpenuhi:
  1. Perangkat USB dengan VID_058F&PID_6387 terdeteksi melalui WMI
     (PNPDeviceID berisi VID_058F&PID_6387), dan
  2. File kunci securevox.key terbaca di salah satu drive USB (removable).

Konfigurasi VID/PID dibaca dari config.json (bagian "dongle").

Fungsi publik:
    cek_dongle()        -> bool
    baca_file_kunci()   -> bytes | None
    registrasi_dongle() -> bool
"""
from __future__ import annotations

import json
import os
import string
from typing import Optional

import wmi

CONFIG_PATH = "config.json"

# Default (digunakan jika config.json tidak ada / tidak dapat dibaca).
DEFAULT_VID = "058F"
DEFAULT_PID = "6387"
DEFAULT_KEY_FILENAME = "securevox.key"
KEY_SIZE = 32  # ukuran file kunci acak saat registrasi, dalam byte


def _load_config() -> dict:
    """Baca config.json. Mengembalikan dict kosong jika gagal."""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


_CFG = _load_config()
_DONGLE_CFG = _CFG.get("dongle", {}) if isinstance(_CFG.get("dongle"), dict) else {}
DONGLE_VID = _DONGLE_CFG.get("vid", DEFAULT_VID).upper()
DONGLE_PID = _DONGLE_CFG.get("pid", DEFAULT_PID).upper()
KEY_FILENAME = _DONGLE_CFG.get("key_filename", DEFAULT_KEY_FILENAME)


def _available_drive_letters() -> list[str]:
    """Daftar akar drive yang terdeteksi (D: s/d Z:) yang siap dibaca."""
    drives: list[str] = []
    for huruf in string.ascii_uppercase[3:]:  # D, E, ..., Z
        drive = f"{huruf}:\\"
        if os.path.exists(drive):
            drives.append(drive)
    return drives


def _is_removable(drive: str) -> bool:
    """Coba apakah drive adalah removable via GetDriveTypeW (Windows).

    Jika ctypes tidak tersedia atau gagal, asumsikan True agar deteksi
    tetap bekerja pada drive USB yang terlihat sebagai fixed.
    """
    try:
        import ctypes

        return ctypes.windll.kernel32.GetDriveTypeW(drive) == 2  # DRIVE_REMOVABLE
    except Exception:
        return True


def _detect_via_wmi() -> bool:
    """Cek apakah ada perangkat USB dengan VID/PID dongle via WMI."""
    try:
        c = wmi.WMI()
        vid_token = f"VID_{DONGLE_VID}"
        pid_token = f"PID_{DONGLE_PID}"
        for entity in c.Win32_PnPEntity():
            pnp = entity.PNPDeviceID or ""
            if vid_token in pnp.upper() and pid_token in pnp.upper():
                return True
    except Exception:
        # WMI tidak tersedia atau error -> tidak bisa memastikan via WMI.
        return False
    return False


def _find_key_drive() -> Optional[str]:
    """Cari drive yang berisi file kunci securevox.key.

    Drive removable diprioritaskan, namun semua drive tersedia D: s/d Z:
    dicoba karena beberapa USB stick terdeteksi sebagai fixed drive oleh
    Windows. Identitas dongle itself sudah dipastikan oleh _detect_via_wmi.
    """
    removable: list[str] = []
    lainnya: list[str] = []
    for drive in _available_drive_letters():
        (removable if _is_removable(drive) else lainnya).append(drive)
    for drive in removable + lainnya:
        path = os.path.join(drive, KEY_FILENAME)
        if os.path.isfile(path):
            return drive
    return None


def cek_dongle() -> bool:
    """True jika dongle sah: VID/PID cocok via WMI dan file kunci terbaca."""
    return _detect_via_wmi() and _find_key_drive() is not None


def cek_info_dongle() -> dict:
    """Deteksi informasi dongle yang tersedia via WMI.

    Mengembalikan dict dengan kunci:
        found: bool - apakah ada USB dengan VID/PID yang cocok
        vid: str - VID yang dicari (dari config.json)
        pid: str - PID yang dicari (dari config.json)
        devices: list[str] - daftar PNPDeviceID yang cocok
    """
    vid_token = f"VID_{DONGLE_VID}"
    pid_token = f"PID_{DONGLE_PID}"
    devices: list[str] = []
    try:
        c = wmi.WMI()
        for entity in c.Win32_PnPEntity():
            pnp = entity.PNPDeviceID or ""
            if vid_token in pnp.upper() and pid_token in pnp.upper():
                devices.append(pnp)
    except Exception:
        pass
    return {
        "found": len(devices) > 0,
        "vid": DONGLE_VID,
        "pid": DONGLE_PID,
        "devices": devices,
    }


def baca_file_kunci() -> Optional[bytes]:
    """Baca isi securevox.key dari drive dongle.

    Mengembalikan bytes isi kunci, atau None jika drive/kunci tidak ditemukan
    atau tidak dapat dibaca.
    """
    drive = _find_key_drive()
    if drive is None:
        return None
    path = os.path.join(drive, KEY_FILENAME)
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def registrasi_dongle() -> bool:
    """Buat file securevox.key (32 byte acak) di drive USB pertama yang tersedia.

    Digunakan saat setup/registrasi dongle. Mengembalikan True jika berhasil
    menulis file kunci, False jika tidak ada drive USB yang dapat ditulis.
    """
    drive = _find_key_drive()
    if drive is None:
        for drive in _available_drive_letters():
            if not _is_removable(drive):
                continue
            path = os.path.join(drive, KEY_FILENAME)
            try:
                with open(path, "wb") as f:
                    f.write(os.urandom(KEY_SIZE))
                return True
            except OSError:
                continue
        return False

    path = os.path.join(drive, KEY_FILENAME)
    try:
        with open(path, "wb") as f:
            f.write(os.urandom(KEY_SIZE))
        return True
    except OSError:
        return False
