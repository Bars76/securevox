"""FaceScreen: verifikasi wajah LBPH (Fase 4).

Alur:
    1. Pengguna daftar wajah (webcam ambil sampel, latihan model LBPH).
    2. Verifikasi wajah (maks. 3 percobaan, threshold dari config.json).
    3. Sukses -> lanjut ke LoginScreen.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import modules.face_auth as face_auth
from ui.widgets.camera_widget import CameraWidget


class FaceScreen(QWidget):
    request_login = Signal()
    request_dongle = Signal()  # kembali ke layar awal (dongle) setelah 3x gagal

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("emptyScreen")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.title = QLabel("Verifikasi Wajah")
        self.title.setObjectName("cardTitle")
        self.title.setAlignment(Qt.AlignCenter)

        self.desc = QLabel(
            "Daftarkan wajah Anda terlebih dahulu, lalu verifikasi. "
            "Maksimum 3 percobaan gagal sebelum ditolak."
        )
        self.desc.setAlignment(Qt.AlignCenter)
        self.desc.setWordWrap(True)

        # Kamera.
        self.camera = CameraWidget()

        # Input username untuk pendaftaran.
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("Username untuk pendaftaran wajah")
        self.user_edit.setFixedWidth(320)

        self.btn_daftar = QPushButton("Daftar Wajah (ambil sampel webcam)")
        self.btn_daftar.clicked.connect(self._daftar_wajah)

        # Verifikasi.
        self.btn_verifikasi = QPushButton("Verifikasi Wajah")
        self.btn_verifikasi.setObjectName("primary")
        self.btn_verifikasi.clicked.connect(self._verifikasi)

        self.percobaan_label = QLabel("Percobaan: 0/3")
        self.percobaan_label.setAlignment(Qt.AlignCenter)
        self.percobaan_label.setObjectName("statusLabel")

        self.status = QLabel("Belum ada verifikasi.")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setObjectName("statusLabel")

        self.btn_lanjut = QPushButton("Lanjut ke Login")
        self.btn_lanjut.setEnabled(False)
        self.btn_lanjut.clicked.connect(self.request_login.emit)

        layout.addWidget(self.title)
        layout.addWidget(self.desc)
        layout.addWidget(self.camera, alignment=Qt.AlignCenter)
        layout.addWidget(self.user_edit, alignment=Qt.AlignCenter)
        layout.addWidget(self.btn_daftar)
        layout.addWidget(self.btn_verifikasi)
        layout.addWidget(self.percobaan_label)
        layout.addWidget(self.status)
        layout.addWidget(self.btn_lanjut)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.camera.start()

    def start(self) -> None:
        self.camera.start()
        self.status.setText("Siap. Daftarkan atau verifikasi wajah.")
        self.percobaan_label.setText("Percobaan: 0/3")
        self.btn_lanjut.setEnabled(False)

    def reset(self) -> None:
        self.user_edit.clear()
        self.status.setText("Belum ada verifikasi.")
        self.percobaan_label.setText("Percobaan: 0/3")
        self.btn_lanjut.setEnabled(False)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.camera.stop()
        super().closeEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self.camera.stop()
        super().hideEvent(event)

    # ------------------------------------------------------------ aksi
    def _daftar_wajah(self) -> None:
        username = self.user_edit.text().strip()
        if not username:
            self._set_status("Username tidak boleh kosong.", "err")
            return

        self.camera.stop()
        self.status.setText("Mengambil sampel wajah dari webcam...")
        self.status.setProperty("status", "err")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

        sukses, pesan = face_auth.daftar_wajah(username)
        self._set_status(pesan, "ok" if sukses else "err")
        if sukses:
            QMessageBox.information(self, "Pendaftaran Wajah", pesan)
        self.camera.start()

    def _verifikasi(self) -> None:
        self.camera.stop()
        self.status.setText("Memverifikasi wajah (max 3 percobaan)...")
        self.status.setProperty("status", "err")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

        sukses, pesan, percobaan = face_auth.verifikasi_wajah()
        self.percobaan_label.setText(f"Percobaan: {percobaan}/3")

        if sukses:
            self._set_status(pesan, "ok")
            self.btn_lanjut.setEnabled(True)
            QMessageBox.information(self, "Verifikasi Berhasil", pesan)
        else:
            self._set_status(pesan, "err")
            if percobaan >= 3:
                QMessageBox.warning(
                    self, "Verifikasi Gagal",
                    "Wajah tidak cocok setelah 3 percobaan. Kembali ke layar awal."
                )
                self.request_dongle.emit()
            else:
                QMessageBox.warning(
                    self, "Verifikasi Gagal",
                    f"Wajah tidak cocok (percobaan {percobaan}/3). Coba lagi."
                )
        self.camera.start()

    def _set_status(self, teks: str, jenis: str) -> None:
        self.status.setText(teks)
        self.status.setProperty("status", jenis)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.update()
