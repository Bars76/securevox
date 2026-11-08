"""DongleScreen: layar pertama. Aplikasi tidak bisa lanjut tanpa dongle sah."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import modules.dongle as dongle


class DongleScreen(QWidget):
    """Layar 'Colokkan Dongle' dengan indikator status.

    Signals:
        request_face: emitted ketika dongle terdeteksi dan siap lanjut ke wajah.
    """

    request_face = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("emptyScreen")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        self.icon_label = QLabel("🔌")
        self.icon_label.setStyleSheet("font-size: 64px;")
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.title = QLabel("Colokkan Dongle SecureVox")
        self.title.setObjectName("cardTitle")
        self.title.setAlignment(Qt.AlignCenter)

        self.desc = QLabel(
            "Masukan USB dongle SecureVox yang terdaftar, lalu klik Deteksi."
        )
        self.desc.setAlignment(Qt.AlignCenter)
        self.desc.setWordWrap(True)

        self.status = QLabel("Menunggu dongle...")
        self.status.setObjectName("statusLabel")
        self.status.setProperty("status", "err")
        self.status.setAlignment(Qt.AlignCenter)

        self.btn_deteksi = QPushButton("Deteksi Dongle")
        self.btn_deteksi.setObjectName("primary")
        self.btn_deteksi.clicked.connect(self._cek_dongle)

        self.btn_lanjut = QPushButton("Lanjut ke Verifikasi Wajah")
        self.btn_lanjut.setEnabled(False)
        self.btn_lanjut.clicked.connect(self.request_face.emit)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title)
        layout.addWidget(self.desc)
        layout.addWidget(self.status)
        layout.addWidget(self.btn_deteksi)
        layout.addWidget(self.btn_lanjut)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.layout().setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

    def reset(self) -> None:
        self.status.setText("Menunggu dongle...")
        self.status.setProperty("status", "err")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.update()
        self.btn_lanjut.setEnabled(False)

    def show_dongle_dicabut(self) -> None:
        self.reset()
        self.status.setText("Dongle dicabut! Aplikasi dikunci.")
        self.status.setProperty("status", "err")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.update()

    def _cek_dongle(self) -> None:
        """Deteksi dongle menggunakan modules.dongle.cek_dongle."""
        if dongle.cek_dongle():
            kunci = dongle.baca_file_kunci()
            if kunci is not None:
                self.status.setText("Dongle terdeteksi dan sah.")
            else:
                self.status.setText("Dongle terdeteksi, namun kunci tidak terbaca.")
            self.status.setProperty("status", "ok")
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            self.status.update()
            self.btn_lanjut.setEnabled(True)
        else:
            self.status.setText("Dongle tidak ditemukan. Silakan coba lagi.")
            self.status.setProperty("status", "err")
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            self.status.update()
            self.btn_lanjut.setEnabled(False)
