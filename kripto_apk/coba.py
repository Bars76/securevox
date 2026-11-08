"""coba.py - Alat uji coba deteksi dongle SecureVox.

Digunakan untuk menguji fitur 'dongle dicabut -> aplikasi mengunci'
tanpa harus mencabut USB secara fisik.

Cara pakai:
    python coba.py
"""
from __future__ import annotations

import os
import shutil
import time

import modules.dongle as dongle

KEY_FILENAME = dongle.KEY_FILENAME


def cari_file_kunci() -> str | None:
    """Cari drive yang berisi securevox.key (D: s/d Z:)."""
    import string

    for huruf in string.ascii_uppercase[3:]:
        drive = f"{huruf}:\\"
        if os.path.exists(drive) and os.path.isfile(os.path.join(drive, KEY_FILENAME)):
            return drive
    return None


def main() -> None:
    print("=== Uji Coba Deteksi Dongle SecureVox ===\n")

    # 1. Cek status dongle saat ini
    info = dongle.cek_info_dongle()
    print(f"VID/PID yang dicari: {info['vid']}/{info['pid']}")
    print(f"Dongle terdeteksi via WMI: {'YA' if info['found'] else 'TIDAK'}")
    print(f"Perangkat cocok: {info['devices']}")

    drive = cari_file_kunci()
    if drive:
        print(f"File kunci ditemukan di: {drive}{KEY_FILENAME}")
    else:
        print("File kunci securevox.key TIDAK ditemukan di drive USB.")
        print("\nTidak dapat melanjutkan uji coba (tidak ada kunci untuk disembunyikan).")
        return

    print("\n--- Simulasi 'dongle dicabut' ---")
    print("File kunci akan disembunyikan sementara (5 detik)...")

    # 2. Sembunyikan file kunci dengan mengganti namanya
    path_asli = os.path.join(drive, KEY_FILENAME)
    path_sembunyi = os.path.join(drive, KEY_FILENAME + ".bak")

    shutil.move(path_asli, path_sembunyi)

    try:
        # 3. Cek status saat "dongle dicabut"
        print(f"\nDeteksi dongle saat kunci disembunyikan: {dongle.cek_dongle()}")
        print("-> Jika False, berarti dongle dianggap dicabut (aman).")
        print("\nTunggu 5 detik (simulasi dongle dicabut)...")
        time.sleep(5)
    finally:
        # 4. Kembalikan file kunci
        shutil.move(path_sembunyi, path_asli)

    # 5. Cek status setelah "dongle dipasang kembali"
    print(f"\nDeteksi dongle setelah kunci dikembalikan: {dongle.cek_dongle()}")
    print("-> Jika True, berarti dongle dianggap dipasang kembali (aman).")

    print("\n=== Uji coba selesai ===")


if __name__ == "__main__":
    main()
