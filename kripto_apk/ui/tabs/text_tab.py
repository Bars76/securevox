"""ui/tabs/text_tab.py - Tab Pesan Teks: Enkripsi 2 Lapisan (Vigenère + AES-256).

Lapisan (sesuai kebutuhan):
    1. Vigenère Cipher (kunci input pengguna)
    2. AES-256-CBC (kunci input pengguna, dimasukkan manual)

Dekripsi dilakukan dengan urutan terbalik: AES-256 → Vigenère.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import modules.crypto_text as ct


class TextTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ---------- kunci (2 kunci input, manual) ----------
        grup_kunci = QGroupBox("Kunci Enkripsi (2 Lapisan)")
        grid = QGridLayout(grup_kunci)

        self.edit_vig = QLineEdit()
        self.edit_vig.setPlaceholderText("Kunci Vigenère (huruf A-Z)")
        self.edit_aes = QLineEdit()
        self.edit_aes.setPlaceholderText("Kunci AES-256 (teks bebas, di-hash otomatis)")

        grid.addWidget(QLabel("1. Vigenère:"), 0, 0)
        grid.addWidget(self.edit_vig, 0, 1)
        grid.addWidget(QLabel("2. AES-256 (manual):"), 1, 0)
        grid.addWidget(self.edit_aes, 1, 1)
        layout.addWidget(grup_kunci)

        # ---------- input / output ----------
        grup_teks = QGroupBox("Pesan Teks (Plaintext vs Ciphertext)")
        hbox = QHBoxLayout(grup_teks)
        self.edit_plain = QTextEdit()
        self.edit_plain.setPlaceholderText("Masukkan plaintext (pesan asli)...")
        self.edit_cipher = QTextEdit()
        self.edit_cipher.setPlaceholderText("Masukkan ciphertext (Base64) untuk didekripsi...")
        # Tidak read-only agar pengguna bisa mengetik/mempel paste ciphertext
        self.edit_cipher.setReadOnly(False)
        hbox.addWidget(self.edit_plain)
        hbox.addWidget(self.edit_cipher)
        layout.addWidget(grup_teks)

        tombol = QHBoxLayout()
        self.btn_enkripsi = QPushButton("Enkripsi (2 Lapisan)")
        self.btn_enkripsi.setObjectName("primary")
        self.btn_enkripsi.clicked.connect(self._enkripsi)
        self.btn_dekripsi = QPushButton("Dekripsi")
        self.btn_dekripsi.clicked.connect(self._dekripsi)
        self.btn_bersih = QPushButton("Bersihkan")
        self.btn_bersih.clicked.connect(self._bersihkan)
        tombol.addWidget(self.btn_enkripsi)
        tombol.addWidget(self.btn_dekripsi)
        tombol.addWidget(self.btn_bersih)
        tombol.addStretch()
        layout.addLayout(tombol)

        # ---------- tiap tahap (wajib ditampilkan untuk demo) ----------
        grup_tahap = QGroupBox("Hasil Setiap Tahap (untuk demonstrasi)")
        th = QVBoxLayout(grup_tahap)
        self.label_plain = QLabel("Plaintext: (belum diproses)")
        self.label_vig = QLabel("1. Hasil Vigenère: (belum diproses)")
        self.label_aes = QLabel("2. Hasil AES-256 (ciphertext akhir): (belum diproses)")
        for lab in (
            self.label_plain,
            self.label_vig,
            self.label_aes,
        ):
            lab.setWordWrap(True)
            lab.setObjectName("statusLabel")
            th.addWidget(lab)
        layout.addWidget(grup_tahap)

        layout.addStretch()

    # ------------------------------------------------------------ aksi
    def _enkripsi(self) -> None:
        plaintext = self.edit_plain.toPlainText().strip()
        kunci_vig = self.edit_vig.text().strip()
        kunci_aes = self.edit_aes.text().strip()
        if not plaintext:
            self._status("Masukkan plaintext terlebih dahulu.", "err")
            return
        if not kunci_vig or not kunci_aes:
            self._status("Masukkan kunci Vigenère dan AES-256.", "err")
            return
        try:
            hasil = ct.enkripsi_dua_lapisan(plaintext, kunci_vig, kunci_aes)
        except Exception as exc:  # noqa: BLE001
            self._status(f"Gagal enkripsi: {exc}", "err")
            return

        self.edit_cipher.setPlainText(hasil.ciphertext_akhir)
        self.label_plain.setText(f"Plaintext: {hasil.plaintext}")
        self.label_vig.setText(f"1. Hasil Vigenère: {hasil.setelah_vigenere}")
        self.label_aes.setText(
            f"2. Hasil AES-256 (ciphertext akhir, Base64): {hasil.ciphertext_akhir}"
        )
        self._status("Enkripsi berhasil (Vigenère → AES-256).", "ok")

    def _dekripsi(self) -> None:
        ciphertext = self.edit_cipher.toPlainText().strip()
        kunci_vig = self.edit_vig.text().strip()
        kunci_aes = self.edit_aes.text().strip()
        if not ciphertext:
            self._status("Masukkan ciphertext terlebih dahulu.", "err")
            return
        if not kunci_vig or not kunci_aes:
            self._status("Masukkan kunci Vigenère dan AES-256.", "err")
            return
        try:
            plaintext = ct.dekripsi_dua_lapisan(ciphertext, kunci_vig, kunci_aes)
        except Exception as exc:  # noqa: BLE001
            self._status(f"Gagal dekripsi: {exc}", "err")
            return

        self.edit_plain.setPlainText(plaintext)
        self.label_plain.setText(f"Plaintext (hasil dekripsi): {plaintext}")
        self.label_vig.setText("1. Hasil Vigenère: (dilewati saat dekripsi)")
        self.label_aes.setText("2. Ciphertext akhir: (dilewati saat dekripsi)")
        self._status("Dekripsi berhasil (AES-256 → Vigenère).", "ok")

    def _bersihkan(self) -> None:
        self.edit_plain.clear()
        self.edit_cipher.clear()
        self.label_plain.setText("Plaintext: (belum diproses)")
        self.label_vig.setText("1. Hasil Vigenère: (belum diproses)")
        self.label_aes.setText("2. Hasil AES-256 (ciphertext akhir): (belum diproses)")
        self._status("")

    def _status(self, teks: str, jenis: str = "") -> None:
        if jenis:
            self.label_plain.setText(f"[{jenis.upper()}] {teks}")
        elif teks:
            self.label_plain.setText(teks)
