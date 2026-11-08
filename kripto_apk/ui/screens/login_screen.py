"""LoginScreen: layar login username + password (Fase 3)."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import modules.login as login_mod


class LoginScreen(QWidget):
    """Layar login.

    Signals:
        request_dashboard(int, str, bytes): user_id, username, master_key
            setelah login berhasil.
    """

    request_dashboard = Signal(int, str, bytes)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("emptyScreen")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)

        self.icon_label = QLabel("🔐")
        self.icon_label.setStyleSheet("font-size: 64px;")
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.title = QLabel("Login")
        self.title.setObjectName("cardTitle")
        self.title.setAlignment(Qt.AlignCenter)

        self.desc = QLabel(
            "Masukkan username dan password. Password disimpan sebagai "
            "hash SHA-256 + salt (tidak pernah disimpan asli)."
        )
        self.desc.setAlignment(Qt.AlignCenter)
        self.desc.setWordWrap(True)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("Username")
        self.user_edit.setFixedWidth(300)

        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Password")
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setFixedWidth(300)

        self.status = QLabel("")
        self.status.setObjectName("statusLabel")
        self.status.setProperty("status", "err")
        self.status.setAlignment(Qt.AlignCenter)

        self.btn_login = QPushButton("Login")
        self.btn_login.setObjectName("primary")
        self.btn_login.clicked.connect(self._proses_login)

        self.btn_daftar = QPushButton("Daftar akun baru")
        self.btn_daftar.clicked.connect(self._proses_daftar)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title)
        layout.addWidget(self.desc)
        layout.addWidget(self.user_edit, alignment=Qt.AlignCenter)
        layout.addWidget(self.pass_edit, alignment=Qt.AlignCenter)
        layout.addWidget(self.status)
        layout.addWidget(self.btn_login)
        layout.addWidget(self.btn_daftar)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.layout().setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

    def reset(self) -> None:
        self.user_edit.clear()
        self.pass_edit.clear()
        self.status.clear()

    # ------------------------------------------------------------ aksi
    def _proses_login(self) -> None:
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()
        sukses, pesan, user_id, master_key = login_mod.login(username, password)

        if sukses and user_id is not None and master_key is not None:
            self.status.setProperty("status", "ok")
            self.status.setText(pesan)
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            self.status.update()
            self.request_dashboard.emit(user_id, username, master_key)
        else:
            self.status.setProperty("status", "err")
            self.status.setText(pesan)
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)
            self.status.update()

    def _proses_daftar(self) -> None:
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()
        sukses, pesan = login_mod.register_user(username, password)

        if sukses:
            self.status.setProperty("status", "ok")
        else:
            self.status.setProperty("status", "err")
        self.status.setText(pesan)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.update()


from PySide6.QtCore import Qt  # noqa: E402
