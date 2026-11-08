"""Dashboard: layar utama setelah login (Fase 3-10).

QTabWidget dengan tab: Pesan Teks, Pesan Audio, Pesan Gambar, Aset (Blockchain), Log.
Tab Pesan Teks diisi Fase 5; sisanya placeholder yang diisi Fase 6-9.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import ui.session as session_mod
from ui.screens.login_screen import LoginScreen  # hanya untuk tipe hint
from ui.tabs.asset_tab import AssetTab
from ui.tabs.image_tab import ImageTab
from ui.tabs.log_tab import LogTab
from ui.tabs.pdf_tab import PdfTab
from ui.tabs.text_tab import TextTab

import modules.database as database_mod


class _PlaceholderTab(QWidget):
    """Tab sementara untuk fitur yang akan diimplementasikan fase berikutnya."""

    def __init__(self, nama: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel(
            f"{nama} akan diimplementasikan pada fase berikutnya sesuai PRD bagian 12."
        )
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("statusLabel")
        layout.addWidget(label)


class Dashboard(QWidget):
    request_logout = Signal()

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header info sesi.
        self.user_label = QLabel("User: (belum login)")
        self.user_label.setAlignment(Qt.AlignCenter)
        self.user_label.setObjectName("statusLabel")
        self.user_label.setProperty("status", "ok")
        self.user_label.setFixedHeight(30)

        self.session_label = QLabel("Sesi: tidak aktif")
        self.session_label.setAlignment(Qt.AlignCenter)
        self.session_label.setObjectName("statusLabel")
        self.session_label.setProperty("status", "err")
        self.session_label.setFixedHeight(30)

        header = QVBoxLayout()
        header.addWidget(self.user_label)
        header.addWidget(self.session_label)
        layout.addLayout(header)

        # Tab fitur.
        self.tabs = QTabWidget()
        self.text_tab = TextTab()
        self.pdf_tab = PdfTab()
        self.image_tab = ImageTab()
        self.asset_tab = AssetTab()
        self.log_tab = LogTab()

        self.tabs.addTab(self.text_tab, "Pesan Teks")
        self.tabs.addTab(self.pdf_tab, "Pesan PDF")
        self.tabs.addTab(self.image_tab, "Pesan Gambar")
        self.tabs.addTab(self.asset_tab, "Aset (Blockchain)")
        self.tabs.addTab(self.log_tab, "Log")
        layout.addWidget(self.tabs)

        # Tombol logout.
        self.btn_logout = QPushButton("Logout")
        self.btn_logout.clicked.connect(self.request_logout.emit)
        self.btn_logout.setFixedHeight(32)
        self.btn_logout.setFixedWidth(120)

        self.btn_db_mentah = QPushButton("Lihat Isi DB Mentah")
        self.btn_db_mentah.clicked.connect(self._lihat_db_mentah)
        self.btn_db_mentah.setFixedHeight(32)
        self.btn_db_mentah.setFixedWidth(160)

        btn_lay = QVBoxLayout()
        btn_lay.addStretch()
        btn_lay.addWidget(self.btn_db_mentah, alignment=Qt.AlignRight)
        btn_lay.addWidget(self.btn_logout, alignment=Qt.AlignRight)
        btn_lay.addStretch()
        layout.addLayout(btn_lay)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)

    def set_master_key(self, master_key: bytes) -> None:
        session_mod.session.master_key = master_key
        self._master_key = master_key

    def refresh(self) -> None:
        if session_mod.session.username:
            self.user_label.setText(f"User: {session_mod.session.username}")
            self.user_label.setProperty("status", "ok")
            self.session_label.setText("Sesi: aktif (Master Key di memori)")
            self.session_label.setProperty("status", "ok")
        else:
            self.user_label.setText("User: (belum login)")
            self.session_label.setText("Sesi: tidak aktif")
            self.session_label.setProperty("status", "err")
        for lab in (self.user_label, self.session_label):
            lab.style().unpolish(lab)
            lab.style().polish(lab)
            lab.update()

    def _lihat_db_mentah(self) -> None:
        """Tampilkan isi tabel messages mentah (ciphertext/Base64) untuk demo."""
        db = database_mod.Database()
        rows = db.get_raw_messages()
        if not rows:
            QMessageBox.information(self, "DB Mentah", "Tabel messages kosong.")
            return
        teks = "Isi tabel `messages` (ciphertext / Base64, enak tidak terbaca):\n\n"
        for r in rows[:10]:
            teks += f"id={r['id']} sender={r['sender']}\n  {r['content_enc'][:80]}...\n\n"
        teks += "\n(Ini adalah ciphertext AES-GCM. Tanpa Master Key, data tidak terbaca.)"
        QMessageBox.information(self, "Isi DB Mentah", teks)


from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QHBoxLayout  # noqa: E402
