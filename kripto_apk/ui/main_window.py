"""MainWindow: jendela utama SecureVox.

Mengatur QStackedWidget dengan empat layar:
    DongleScreen -> FaceScreen -> LoginScreen -> Dashboard

Header selalu menampilkan indikator status dongle (hijau/merah). Pemeriksaan
dongle berjalan di background thread (DongleWorker) setiap 3 detik. Jika USB
dicabut selama aplikasi berjalan, Master Key dihapus dan aplikasi dikunci
kembali ke layar dongle.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.session import session
from ui.screens.dashboard import Dashboard
from ui.screens.dongle_screen import DongleScreen
from ui.screens.face_screen import FaceScreen
from ui.screens.login_screen import LoginScreen
from ui.workers import DongleWorker

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SecureVox - Pesan Aman Multimedia")
        self.resize(1200, 780)
        self.setMinimumSize(900, 600)

        self._dongle_online: Optional[bool] = None
        self._dongle_worker: Optional[DongleWorker] = None

        self._build_header()
        self._build_stacked_widget()

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.header)
        central_layout.addWidget(self.stack)
        self.setCentralWidget(central)

        # Mulai dengan layar dongle.
        self.stack.setCurrentWidget(self.dongle_screen)

        # Worker polling dongle di background thread (3 detik).
        self._dongle_worker = DongleWorker(interval_ms=3000)
        self._dongle_worker.status_changed.connect(self._on_dongle_status_changed)
        self._dongle_worker.start()

    # ------------------------------------------------------------------ UI
    def _build_header(self) -> None:
        self.header = QWidget()
        self.header.setObjectName("header")
        self.header.setFixedHeight(72)

        layout = QHBoxLayout(self.header)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(16)

        logo = QLabel("SECUREVOX")
        logo.setObjectName("logoLabel")

        tagline = QLabel("Pesan Aman Multimedia  •  Dongle + Wajah + Enkripsi")
        tagline.setObjectName("taglineLabel")

        self.dongle_label = QLabel("Dongle: memeriksa...")
        self.dongle_label.setObjectName("dongleStatus")
        self.dongle_label.setProperty("online", "false")
        self.dongle_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(logo)
        layout.addWidget(tagline)
        layout.addStretch()
        layout.addWidget(self.dongle_label)

    def _build_stacked_widget(self) -> None:
        self.stack = QStackedWidget()

        self.dongle_screen = DongleScreen()
        self.face_screen = FaceScreen()
        self.login_screen = LoginScreen()
        self.dashboard = Dashboard()

        self.stack.addWidget(self.dongle_screen)
        self.stack.addWidget(self.face_screen)
        self.stack.addWidget(self.login_screen)
        self.stack.addWidget(self.dashboard)

        # Hubungkan navigasi antar layar.
        self.dongle_screen.request_face.connect(self.show_face)
        self.face_screen.request_login.connect(self.show_login)
        self.face_screen.request_dongle.connect(self.show_dongle)
        self.login_screen.request_dashboard.connect(self.show_dashboard)
        self.dashboard.request_logout.connect(self.show_dongle)
    # ------------------------------------------------------------- navigasi
    def show_dongle(self) -> None:
        session.clear()
        self.stack.setCurrentWidget(self.dongle_screen)
        self.dongle_screen.reset()

    def show_face(self) -> None:
        self.stack.setCurrentWidget(self.face_screen)
        self.face_screen.start()

    def show_login(self) -> None:
        self.stack.setCurrentWidget(self.login_screen)
        self.login_screen.reset()

    def show_dashboard(self, user_id: int, username: str, master_key: bytes) -> None:
        session.set_user(user_id, username, master_key)
        self.dashboard.set_master_key(master_key)
        self.stack.setCurrentWidget(self.dashboard)
        self.dashboard.refresh()

    # ------------------------------------------------------- polling dongle
    def _on_dongle_status_changed(self, online: bool) -> None:
        """Dipanggil dari DongleWorker via signal (jalan di GUI thread)."""
        if online == self._dongle_online:
            return
        self._dongle_online = online
        self._update_dongle_indicator(online)
        if not online:
            # Dongle dicabut selama aplikasi berjalan -> kunci aplikasi.
            session.clear()
            self.stack.setCurrentWidget(self.dongle_screen)
            self.dongle_screen.show_dongle_dicabut()

    def _update_dongle_indicator(self, online: bool) -> None:
        self.dongle_label.setProperty("online", "true" if online else "false")
        if online:
            self.dongle_label.setText("Dongle: terpasang (aman)")
        else:
            self.dongle_label.setText("Dongle: DICABUT - aplikasi dikunci")
        self.dongle_label.style().unpolish(self.dongle_label)
        self.dongle_label.style().polish(self.dongle_label)
        self.dongle_label.update()

    def closeEvent(self, event) -> None:  # noqa: N802
        session.clear()
        if self._dongle_worker:
            self._dongle_worker.stop()
        super().closeEvent(event)
