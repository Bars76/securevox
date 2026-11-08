"""ui/tabs/asset_tab.py - Tab Aset: Blockchain Sederhana dengan PoW."""
from __future__ import annotations

import os
import time

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import modules.blockchain as bc
from ui.session import session


class AssetTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ---------- tambah aset ----------
        grup_in = QGroupBox("Tambah Aset ke Blockchain")
        hb = QHBoxLayout(grup_in)
        self.edit_nama = QLineEdit()
        self.edit_nama.setPlaceholderText("Nama aset (mis. Dokumen Rahasia)")
        self.btn_pilih_file = QPushButton("Pilih File Aset")
        self.btn_pilih_file.clicked.connect(self._pilih_file)
        self.btn_tambah = QPushButton("Tambah Aset (Buat Blok + PoW)")
        self.btn_tambah.setObjectName("primary")
        self.btn_tambah.clicked.connect(self._tambah_aset)
        hb.addWidget(self.edit_nama)
        hb.addWidget(self.btn_pilih_file)
        hb.addWidget(self.btn_tambah)
        hb.addStretch()
        layout.addWidget(grup_in)

        self.path_file: str | None = None
        self.label_file = QLabel("Belum ada file aset dipilih.")
        self.label_file.setWordWrap(True)
        self.label_file.setObjectName("statusLabel")
        layout.addWidget(self.label_file)

        # ---------- aksi chain ----------
        grup_aksi = QGroupBox("Aksi Rantai Blok")
        hb2 = QHBoxLayout(grup_aksi)
        self.btn_validasi = QPushButton("Validasi Chain")
        self.btn_validasi.clicked.connect(self._validasi)
        self.btn_verifikasi = QPushButton("Verifikasi File Aset")
        self.btn_verifikasi.clicked.connect(self._verifikasi_aset)
        self.btn_manipulasi = QPushButton("Simulasi Manipulasi Blok")
        self.btn_manipulasi.clicked.connect(self._manipulasi)
        hb2.addWidget(self.btn_validasi)
        hb2.addWidget(self.btn_verifikasi)
        hb2.addWidget(self.btn_manipulasi)
        hb2.addStretch()
        layout.addWidget(grup_aksi)

        # ---------- tabel chain ----------
        self.tabel = QTableWidget()
        self.tabel.setColumnCount(8)
        self.tabel.setHorizontalHeaderLabels(
            ["Index", "Waktu", "Nama Aset", "File Hash", "Pemilik",
             "Hash Blok", "Previous Hash", "Nonce"]
        )
        self.tabel.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabel.setAlternatingRowColors(True)
        layout.addWidget(self.tabel)

        self.label_status = QLabel("Siap.")
        self.label_status.setObjectName("statusLabel")
        layout.addWidget(self.label_status)

        self._refresh_tabel()

    # ------------------------------------------------------------ aksi
    def _pilih_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Pilih File Aset", "", "Semua File (*.*)")
        if path:
            self.path_file = path
            self.label_file.setText(f"File: {path}")
            self._status("File aset dipilih.", "ok")

    def _tambah_aset(self) -> None:
        nama = self.edit_nama.text().strip()
        if not nama:
            self._status("Masukkan nama aset terlebih dahulu.", "err")
            return
        if not self.path_file or not os.path.isfile(self.path_file):
            self._status("Pilih file aset terlebih dahulu.", "err")
            return
        try:
            rantai = bc.Blockchain()
            blok = rantai.tambah_aset(nama, self.path_file, session.username or "tidak diketahui")
            self._status(
                f"Blok {blok['index']} ditambahkan. Nonce={blok['nonce']}, Hash={blok['hash'][:16]}..."
            )
            self.edit_nama.clear()
            self.path_file = None
            self.label_file.setText("Belum ada file aset dipilih.")
            self._refresh_tabel()
        except Exception as exc:  # noqa: BLE001
            self._status(f"Gagal menambah aset: {exc}", "err")

    def _validasi(self) -> None:
        rantai = bc.Blockchain()
        valid, rusak = rantai.validasi_chain()
        if valid:
            self._status(f"Rantai blok VALID ({len(rantai.chain)} blok).", "ok")
            QMessageBox.information(self, "Validasi Chain", f"Rantai blok VALID.\nJumlah blok: {len(rantai.chain)}")
        else:
            self._status(f"Rantai blok RUSAK pada blok {rusak}.", "err")
            QMessageBox.warning(
                self, "Validasi Chain",
                f"Rantai blok TIDAK VALID.\nBlok yang rusak: {rusak}"
            )

    def _verifikasi_aset(self) -> None:
        nama = self.edit_nama.text().strip()
        if not nama:
            self._status("Masukkan nama aset untuk diverifikasi.", "err")
            return
        rantai = bc.Blockchain()
        cocok, pesan, idx = rantai.verifikasi_aset(nama)
        if cocok:
            self._status(pesan, "ok")
            QMessageBox.information(self, "Verifikasi Aset", pesan)
        else:
            self._status(pesan, "err")
            QMessageBox.warning(self, "Verifikasi Aset", pesan)

    def _manipulasi(self) -> None:
        rantai = bc.Blockchain()
        if len(rantai.chain) <= 1:
            self._status("Belum ada blok selain genesis untuk dimanipulasi.", "err")
            return
        idx = len(rantai.chain) - 1  # manipulasi blok terakhir (selain genesis)
        blok = rantai.chain[idx]
        data_baru = dict(blok["data"])
        data_baru["file_hash"] = "DIUBAH_OLEH_DEMO"
        rantai.simulasi_manipulasi(idx, data_baru)
        self._status(f"Demo: blok {idx} dimanipulasi. Klik Validasi Chain untuk deteksi.", "err")
        self._refresh_tabel()

    def _refresh_tabel(self) -> None:
        rantai = bc.Blockchain()
        chain = rantai.lihat_chain()
        self.tabel.setRowCount(len(chain))
        for r, blok in enumerate(chain):
            data = blok.get("data", {})
            nilai = [
                str(blok["index"]),
                time.strftime("%H:%M:%S", time.localtime(blok["timestamp"])),
                str(data.get("asset_name", "")),
                str(data.get("file_hash", ""))[:16] + "...",
                str(data.get("owner", "")),
                str(blok["hash"])[:16] + "...",
                str(blok["previous_hash"])[:12] + "...",
                str(blok["nonce"]),
            ]
            for c, v in enumerate(nilai):
                item = QTableWidgetItem(v)
                self.tabel.setItem(r, c, item)
        self.tabel.resizeColumnsToContents()

    def _status(self, teks: str, jenis: str = "") -> None:
        self.label_status.setText(teks)
