"""ui/tabs/image_tab.py - Tab Pesan Gambar: Steganografi LSB pada PNG.

Alur yang mudah dipahami:
    1. Pilih cover PNG & masukkan pesan rahasia
    2. Pilih mode (AES + LSB atau LSB saja)
    3. Sisipkan atau ekstrak pesan
    4. Lihat perbandingan gambar asli vs stego
"""
from __future__ import annotations

import os

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import modules.stego as stego
from ui.session import session


def _pixmap_dari_path(path: str, lebar: int = 320) -> QPixmap:
    pix = QPixmap(path)
    return pix.scaledToWidth(lebar, Qt.SmoothTransformation)


class ImageTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ==================================================== LANGKAH 1: PILIH COVER & PESAN
        grup_input = QGroupBox("Langkah 1: Pilih Cover PNG & Masukkan Pesan")
        h1 = QHBoxLayout(grup_input)
        self.btn_pilih_cover = QPushButton("Pilih Cover PNG")
        self.btn_pilih_cover.clicked.connect(self._pilih_cover)
        self.edit_pesan = QTextEdit()
        self.edit_pesan.setPlaceholderText("Masukkan pesan rahasia yang akan disisipkan...")
        self.edit_pesan.setFixedHeight(80)
        h1.addWidget(self.btn_pilih_cover)
        h1.addWidget(self.edit_pesan, stretch=1)
        h1.addStretch()
        layout.addWidget(grup_input)

        self.path_cover: str | None = None
        self.label_cover = QLabel("Belum ada cover dipilih.")
        self.label_cover.setWordWrap(True)
        self.label_cover.setObjectName("statusLabel")
        layout.addWidget(self.label_cover)

        # ==================================================== LANGKAH 2: PILIH MODE
        grup_mode = QGroupBox("Langkah 2: Pilih Mode Steganografi")
        hb_mode = QHBoxLayout(grup_mode)
        self.radio_aes_lsb = QRadioButton("AES + LSB (enkripsi dulu, lalu disisipkan - aman)")
        self.radio_lsb_saja = QRadioButton("LSB saja (tanpa enkripsi)")
        self.radio_aes_lsb.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_aes_lsb, 1)
        self.mode_group.addButton(self.radio_lsb_saja, 0)
        hb_mode.addWidget(self.radio_aes_lsb)
        hb_mode.addWidget(self.radio_lsb_saja)
        hb_mode.addStretch()
        layout.addWidget(grup_mode)

        # ==================================================== LANGKAH 3: AKSI
        grup_aksi = QGroupBox("Langkah 3: Sisipkan atau Ekstrak")
        hb = QHBoxLayout(grup_aksi)
        self.btn_pilih_stego = QPushButton("Pilih Stego (untuk ekstraksi)")
        self.btn_pilih_stego.clicked.connect(self._pilih_stego)
        self.btn_sisip = QPushButton("🔒 Sisipkan Pesan")
        self.btn_sisip.setObjectName("primary")
        self.btn_sisip.clicked.connect(self._sisipkan)
        self.btn_ekstrak = QPushButton("🔓 Ekstrak Pesan")
        self.btn_ekstrak.clicked.connect(self._ekstrak)
        hb.addWidget(self.btn_pilih_stego)
        hb.addWidget(self.btn_sisip)
        hb.addWidget(self.btn_ekstrak)
        hb.addStretch()
        layout.addWidget(grup_aksi)

        self.path_stego: str | None = None
        self.label_file = QLabel("Belum ada stego dipilih.")
        self.label_file.setWordWrap(True)
        self.label_file.setObjectName("statusLabel")
        layout.addWidget(self.label_file)

        # ==================================================== PREVIEW GAMBAR
        grup_banding = QGroupBox("Perbandingan Gambar Asli vs Stego")
        hb2 = QHBoxLayout(grup_banding)
        self.label_gambar_asli = QLabel("Gambar Asli")
        self.label_gambar_asli.setAlignment(Qt.AlignCenter)
        self.label_gambar_stego = QLabel("Gambar Stego")
        self.label_gambar_stego.setAlignment(Qt.AlignCenter)
        self.label_gambar_asli.setMinimumSize(320, 240)
        self.label_gambar_stego.setMinimumSize(320, 240)
        for lab in (self.label_gambar_asli, self.label_gambar_stego):
            lab.setStyleSheet(
                "background-color: #0f1420; border: 1px solid #334155; border-radius: 6px;"
            )
            lab.setScaledContents(True)
        hb2.addWidget(self.label_gambar_asli)
        hb2.addWidget(self.label_gambar_stego)
        layout.addWidget(grup_banding)

        # ==================================================== HASIL
        grup_out = QGroupBox("Hasil")
        out_layout = QVBoxLayout(grup_out)
        self.label_hasil = QLabel("Belum ada proses steganografi.")
        self.label_hasil.setWordWrap(True)
        self.label_hasil.setObjectName("statusLabel")
        out_layout.addWidget(self.label_hasil)
        layout.addWidget(grup_out)

        layout.addStretch()

    # ------------------------------------------------------------ aksi
    def _cek_master_key(self) -> bool:
        if not session.is_authenticated or session.master_key is None:
            self._status("Belum login / Master Key tidak ada di memori.", "err")
            return False
        return True

    def _pilih_cover(self) -> None:
        if not self._cek_master_key():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Gambar Cover", "", "Gambar PNG (*.png)"
        )
        if path:
            self.path_cover = path
            self.label_cover.setText(f"Cover: {os.path.basename(path)}")
            self.label_gambar_asli.setPixmap(_pixmap_dari_path(path))
            self._status("Cover PNG berhasil dipilih.", "ok")

    def _pilih_stego(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Gambar Stego", "", "Gambar PNG (*.png)"
        )
        if path:
            self.path_stego = path
            self.label_file.setText(f"Stego: {os.path.basename(path)}")
            self.label_gambar_stego.setPixmap(_pixmap_dari_path(path))
            self._status("Gambar stego berhasil dipilih. Siap untuk diekstrak.", "ok")

    def _sisipkan(self) -> None:
        if not self.path_cover or not os.path.isfile(self.path_cover):
            self._status("Pilih gambar cover PNG terlebih dahulu.", "err")
            return
        pesan = self.edit_pesan.toPlainText().strip()
        if not pesan:
            self._status("Masukkan pesan rahasia terlebih dahulu.", "err")
            return

        enkripsi_awal = self.radio_aes_lsb.isChecked()
        if enkripsi_awal and not self._cek_master_key():
            return

        default_out = self.path_cover.rsplit(".", 1)[0] + "_stego.png"
        path_out, _ = QFileDialog.getSaveFileName(
            self, "Simpan Gambar Stego", default_out, "PNG (*.png)"
        )
        if not path_out:
            return
        if not path_out.lower().endswith(".png"):
            path_out += ".png"

        try:
            info, psnr = stego.sisipkan_pesan(
                self.path_cover, pesan, session.master_key, path_out,
                enkripsi_awal=enkripsi_awal
            )
            self.path_stego = path_out
            self.label_file.setText(f"Stego: {os.path.basename(path_out)}")
            self.label_gambar_stego.setPixmap(_pixmap_dari_path(path_out))
            mode_teks = "AES + LSB" if enkripsi_awal else "LSB saja"
            self.label_hasil.setText(
                f"✅ Berhasil disisipkan! [{mode_teks}]\n"
                f"Bit disisipkan: {info['bit_disipkan']} / kapasitas: {info['kapasitas_bit']}\n"
                f"PSNR (asli vs stego): {psnr:.2f} dB  (semakin tinggi semakin mirip)"
            )
            self._status(f"Steganografi berhasil ({mode_teks}).", "ok")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Gagal Sisipkan", str(exc))
            self._status(f"Gagal: {exc}", "err")

    def _ekstrak(self) -> None:
        if not self.path_stego or not os.path.isfile(self.path_stego):
            self._status("Pilih gambar stego terlebih dahulu (1 file cukup).", "err")
            return

        enkripsi_awal = self.radio_aes_lsb.isChecked()
        if enkripsi_awal and not self._cek_master_key():
            return
        try:
            pesan = stego.ekstrak_pesan(
                self.path_stego, session.master_key, enkripsi_awal=enkripsi_awal
            )
            psnr = stego.hitung_psnr(
                self.path_cover or self.path_stego, self.path_stego
            )
            self.edit_pesan.setPlainText(pesan)
            mode_teks = "AES + LSB" if enkripsi_awal else "LSB saja"
            self.label_hasil.setText(
                f"✅ Pesan diekstrak [{mode_teks}].\nPSNR: {psnr:.2f} dB"
            )
            self._status(f"Ekstraksi berhasil ({mode_teks}).", "ok")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Gagal Ekstrak", str(exc))
            self._status(f"Gagal: {exc}", "err")

    def _status(self, teks: str, jenis: str = "") -> None:
        self.label_hasil.setText(teks)
