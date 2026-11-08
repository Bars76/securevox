"""modules/face_auth.py - Verifikasi wajah LBPH (logika murni, tanpa PySide6).

- Pendaftaran: ambil 15-30 sampel wajah dari webcam, simpan ke
  data/faces/<username>/ dan latih model LBPH ke data/faces/lbph_model.yml.
- Verifikasi: tangkap wajah, bandingkan dengan model, threshold dapat diatur
  di config.json (bagian "face.threshold").
- Maksimum 3 percobaan gagal, lalu ditolak.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from typing import Optional, Tuple

import cv2
import numpy as np

CONFIG_PATH = "config.json"
FACES_DIR = "data/faces"
MODEL_PATH = os.path.join(FACES_DIR, "lbph_model.yml")
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

SAMPLE_TARGET = 20  # jumlah sampel wajah saat pendaftaran

# Rentang warna kulit di ruang YCrCb (fallback jika file Haar cascade tidak ada).
SKIN_YCRCB_MIN = np.array([0, 133, 77], dtype=np.uint8)
SKIN_YCRCB_MAX = np.array([255, 173, 127], dtype=np.uint8)


def _load_face_config() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("face", {}) if isinstance(cfg, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


_FACE_CFG = _load_face_config()
FACE_THRESHOLD = float(_FACE_CFG.get("threshold", 70.0))
MAX_ATTEMPTS = int(_FACE_CFG.get("max_attempts", 3))
SAMPLES = int(_FACE_CFG.get("samples", SAMPLE_TARGET))


_CASCADE = None


def _muat_cascade() -> Optional[cv2.CascadeClassifier]:
    """Muat Haar cascade jika file xml tersedia secara lokal.

    Mengembalikan None jika file tidak ditemukan (tidak ada unduhan eksternal;
    fallback deteksi wajah akan digunakan).
    """
    global _CASCADE
    if _CASCADE is not False:  # None = belum dicoba, False = gagal
        if os.path.isfile(CASCADE_PATH):
            cls = cv2.CascadeClassifier(CASCADE_PATH)
            if not cls.empty():
                _CASCADE = cls
                return _CASCADE
        _CASCADE = False
    return None


def _deteksi_wajah_fallback(frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Deteksi area berwarna kulit sebagai pengganti deteksi wajah.

    Digunakan hanya ketika file Haar cascade XML tidak tersedia secara lokal.
    Mengembalikan daftar (x, y, w, h).
    """
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, SKIN_YCRCB_MIN, SKIN_YCRCB_MAX)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.dilate(mask, np.ones((7, 7), np.uint8), iterations=2)
    kontur, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hasil: list[tuple[int, int, int, int]] = []
    for c in kontur:
        area = cv2.contourArea(c)
        if area < 3000:
            continue
        x, y, w, h = cv2.boundingRect(c)
        # Perbesar sedikit sekeliling area kulit.
        pad = int(min(w, h) * 0.25)
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(frame.shape[1] - x, w + 2 * pad)
        h = min(frame.shape[0] - y, h + 2 * pad)
        hasil.append((x, y, w, h))
    return hasil


def _deteksi_wajah(frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Deteksi wajah (Haar jika tersedia, otherwise fallback kulit)."""
    cls = _muat_cascade()
    if cls is not None:
        abu = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        deteksi = cls.detectMultiScale(
            abu, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )
        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in deteksi]
    return _deteksi_wajah_fallback(frame)


def _ambil_wajah(frame: np.ndarray) -> Optional[np.ndarray]:
    """Deteksi wajah terbesar dalam frame, kembalikan grayscale ROI 200x200."""
    abu = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    wajahs = _deteksi_wajah(frame)
    if len(wajahs) == 0:
        return None
    # Pilih wajah yang lebarnya terbesar.
    x, y, w, h = max(wajahs, key=lambda b: b[2])
    roi = abu[y : y + h, x : x + w]
    return cv2.resize(roi, (200, 200))


def daftar_wajah(username: str, max_sampel: int = SAMPLES) -> Tuple[bool, str]:
    """
    Daftar wajah baru untuk username.

    Mengambil sampel wajah dari webcam (index 0), menyimpan gambar grayscale
    ke data/faces/<username>/, lalu melatih ulang model LBPH gabungan.

    Mengembalikan (sukses, pesan).
    """
    if not username:
        return False, "Username tidak boleh kosong."

    folder_user = os.path.join(FACES_DIR, username)
    os.makedirs(folder_user, exist_ok=True)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        # Coba backend default jika DSHOW gagal.
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        shutil.rmtree(folder_user, ignore_errors=True)
        return False, "Kamera tidak dapat dibuka."

    jumlah = 0
    try:
        while jumlah < max_sampel:
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            wajah = _ambil_wajah(frame)
            if wajah is not None:
                nama_file = os.path.join(folder_user, f"sampel_{jumlah:02d}.png")
                cv2.imwrite(nama_file, wajah)
                jumlah += 1
            # Jeda singkat agar sampel bervariasi.
            time.sleep(0.1)
    finally:
        cap.release()

    if jumlah < 5:
        shutil.rmtree(folder_user, ignore_errors=True)
        return False, f"Terlalu sedikit sampel wajah ({jumlah}). Coba lagi."

    return _latih_model()


def _kumpulkan_data_latih() -> Tuple[list[np.ndarray], list[int], dict[int, str]]:
    """Kumpulkan semua sampel wajah dari data/faces/* untuk pelatihan."""
    wajahs: list[np.ndarray] = []
    label_ids: list[int] = []
    id_ke_nama: dict[int, str] = {}
    label_id = 0

    if not os.path.isdir(FACES_DIR):
        return wajahs, label_ids, id_ke_nama

    for nama_user in sorted(os.listdir(FACES_DIR)):
        folder = os.path.join(FACES_DIR, nama_user)
        if not os.path.isdir(folder):
            continue
        id_ke_nama[label_id] = nama_user
        for berkas in os.listdir(folder):
            if not berkas.lower().endswith((".png", ".jpg", ".pgm")):
                continue
            path = os.path.join(folder, berkas)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            wajahs.append(img)
            label_ids.append(label_id)
        label_id += 1

    return wajahs, label_ids, id_ke_nama


def _latih_model() -> Tuple[bool, str]:
    """Latih model LBPH dari semua sampel dan simpan ke lbph_model.yml."""
    wajahs, label_ids, id_ke_nama = _kumpulkan_data_latih()
    if len(wajahs) == 0:
        return False, "Tidak ada sampel wajah untuk melatih model."

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(wajahs, np.array(label_ids, dtype=np.int32))
    recognizer.write(MODEL_PATH)

    # Simpan mapping id -> nama sebagai JSON di samping model.
    mapping_path = os.path.join(FACES_DIR, "label_mapping.json")
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(id_ke_nama, f, ensure_ascii=False, indent=2)

    return True, f"Model wajah dilatih ({len(wajahs)} sampel, {len(id_ke_nama)} user)."


def _muat_model() -> Optional[cv2.face_LBPHFaceRecognizer]:
    if not os.path.isfile(MODEL_PATH):
        return None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)
    return recognizer


def _muat_mapping() -> dict[int, str]:
    path = os.path.join(FACES_DIR, "label_mapping.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {int(k): v for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        return {}


def verifikasi_wajah(
    max_percobaan: int = MAX_ATTEMPTS, threshold: Optional[float] = None
) -> Tuple[bool, str, int]:
    """
    Verifikasi wajah melalui webcam.

    Mengembalikan (sukses, pesan, jumlah_percobaan).
    Jika gagal sebanyak max_percobaan, kembali (False, pesan, percobaan).
    """
    if threshold is None:
        threshold = FACE_THRESHOLD

    recognizer = _muat_model()
    if recognizer is None:
        return False, "Belum ada wajah yang terdaftar. Daftarkan dulu.", 0

    mapping = _muat_mapping()
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False, "Kamera tidak dapat dibuka.", 0

    percobaan = 0
    try:
        while percobaan < max_percobaan:
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            percobaan += 1
            wajah = _ambil_wajah(frame)
            if wajah is None:
                continue
            label_id, confidence = recognizer.predict(wajah)
            # LBPH confidence: semakin kecil semakin mirip.
            nama = mapping.get(label_id, "tidak diketahui")
            if confidence <= threshold:
                return True, f"Wajah cocok: {nama} (confidence {confidence:.1f})", percobaan
            # Jika wajah terdeteksi tapi tidak cocok, lanjut percobaan berikutnya.
            time.sleep(0.3)
    finally:
        cap.release()

    return (
        False,
        f"Wajah tidak cocok setelah {percobaan} percobaan.",
        percobaan,
    )


def wajah_terdaftar(username: str) -> bool:
    """Cek apakah username sudah memiliki sampel wajah terdaftar."""
    folder = os.path.join(FACES_DIR, username)
    return os.path.isdir(folder) and any(
        f.lower().endswith((".png", ".jpg", ".pgm")) for f in os.listdir(folder)
    )


def hapus_pendaftaran(username: str) -> bool:
    """Hapus data wajah pengguna (untuk pengujian / reset)."""
    folder = os.path.join(FACES_DIR, username)
    if os.path.isdir(folder):
        shutil.rmtree(folder)
        return _latih_model()[0]
    return False
