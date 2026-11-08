"""ui/widgets/camera_widget.py - Preview kamera dengan deteksi wajah (PySide6).

CameraWorker(QThread) menangkap frame dari OpenCV, mendeteksi wajah,
menggambar kotak deteksi, dan mengirim QImage ke GUI thread via signal.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

import modules.face_auth as face_auth


class CameraWorker(QThread):
    """Thread kamera: capture frame, deteksi wajah, kirim QImage."""

    frame_ready = Signal(object)  # QImage
    status_ready = Signal(str)  # teks status
    wajah_ditemukan = Signal(bool)  # ada wajah atau tidak

    def __init__(self, kamera_index: int = 0, parent=None) -> None:
        super().__init__(parent)
        self.kamera_index = kamera_index
        self._running = True
        self._deteksi = True

    def run(self) -> None:
        cap = cv2.VideoCapture(self.kamera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.kamera_index)
        if not cap.isOpened():
            self.status_ready.emit("Kamera tidak dapat dibuka.")
            return

        self.status_ready.emit("Kamera siap. Arahkan wajah ke kamera.")
        try:
            while self._running:
                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.05)
                    continue

                display = frame.copy()
                ada_wajah = False
                if self._deteksi:
                    wajahs = face_auth._deteksi_wajah(frame)
                    if len(wajahs) > 0:
                        ada_wajah = True
                        (x, y, w, h) = max(wajahs, key=lambda b: b[2])
                        cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 136), 2)
                        cv2.putText(
                            display,
                            "Wajah terdeteksi",
                            (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 136),
                            2,
                        )

                self.wajah_ditemukan.emit(ada_wajah)

                # Konversi BGR -> RGB -> QImage.
                rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qimg = QImage(
                    rgb.data, w, h, bytes_per_line, QImage.Format_RGB888
                ).copy()  # copy agar data aman setelah frame ditimpa
                self.frame_ready.emit(qimg)

                time.sleep(1 / 30)
        finally:
            cap.release()

    def stop(self) -> None:
        self._running = False
        self.wait(2000)


class CameraWidget(QWidget):
    """Widget preview kamera dengan kotak deteksi wajah."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.label_preview = QLabel("Kamera belum dihidupkan.")
        self.label_preview.setAlignment(Qt.AlignCenter)
        self.label_preview.setStyleSheet(
            "background-color: #0f1420; border: 1px solid #334155; border-radius: 6px;"
        )
        self.label_preview.setMinimumSize(640, 480)

        self.label_status = QLabel("Menunggu kamera...")
        self.label_status.setAlignment(Qt.AlignCenter)
        self.label_status.setObjectName("statusLabel")

        layout = QVBoxLayout(self)
        layout.addWidget(self.label_preview)
        layout.addWidget(self.label_status)

        self._worker_thread: CameraWorker | None = None

    def start(self) -> None:
        if self._worker_thread is not None:
            return
        self._worker_thread = CameraWorker()
        self._worker_thread.frame_ready.connect(self._tampilkan_frame)
        self._worker_thread.status_ready.connect(
            lambda t: self.label_status.setText(t)
        )
        self._worker_thread.start()

    def stop(self) -> None:
        if self._worker_thread is not None:
            self._worker_thread.stop()
            self._worker_thread = None

    def _tampilkan_frame(self, qimg: QImage) -> None:
        self.label_preview.setPixmap(
            QPixmap.fromImage(qimg).scaled(
                self.label_preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def capture_frame_bgr(self) -> None:
        """Placeholder agar kompatibel; capture sebenarnya di worker."""
        pass


# Catatan: CameraWorker diimpor sebagai atribut instance, jadi forward-ref di atas
# hanya untuk dokumentasi. Tidak ada dependensi siklik.
