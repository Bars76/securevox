"""ui/tabs/pdf_tab.py - Tab Pesan PDF: Enkripsi & Dekripsi File PDF dengan ChaCha20.

Alur:
    Langkah 1: Pilih file PDF & masukkan deskripsi
    Langkah 2: Enkripsi dengan ChaCha20, simpan ke .enc + database
    Langkah 3: Pilih file .enc dari tabel, lalu Dekripsi & Simpan kembali
    Langkah 4: Lihat daftar file yang telah dienkripsi
"""
from __future__ import annotations

import os

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

import modules.crypto_file as cf
import modules.database as db_mod
from ui.session import session


class PdfTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ==================================================== LANGKAH 1: PILIH FILE & DESKRIPSI
        grup_input = QGroupBox("Langkah 1: Pilih File PDF & Deskripsi")
        h1 = QHBoxLayout(grup_input)
        self.btn_pilih = QPushButton("Pilih File PDF")
        self.btn_pilih.clicked.connect(self._pilih_pdf)
        self.edit_deskripsi = QLineEdit()
        self.edit_deskripsi.setPlaceholderText("Deskripsi file (mis. Laporan Keuangan Q3)...")
        h1.addWidget(self.btn_pilih)
        h1.addWidget(self.edit_deskripsi, stretch=1)
        h1.addStretch()
        layout.addWidget(grup_input)

        self.path_pdf: str | None = None
        self.ekstensi: str | None = None
        self.label_file = QLabel("Belum ada file dipilih.")
        self.label_file.setWordWrap(True)
        self.label_file.setObjectName("statusLabel")
        layout.addWidget(self.label_file)

        # ==================================================== LANGKAH 2: ENKRIPSI
        grup_enkripsi = QGroupBox("Langkah 2: Enkripsi ChaCha20")
        h2 = QHBoxLayout(grup_enkripsi)
        self.btn_enkripsi = QPushButton("🔒 Enkripsi & Simpan (.enc)")
        self.btn_enkripsi.setObjectName("primary")
        self.btn_enkripsi.clicked.connect(self._enkripsi)
        h2.addWidget(self.btn_enkripsi)
        h2.addStretch()
        layout.addWidget(grup_enkripsi)

        self.label_info = QLabel("")
        self.label_info.setWordWrap(True)
        self.label_info.setObjectName("statusLabel")
        layout.addWidget(self.label_info)

        self.label_hex = QLabel("Ciphertext (hex): (belum ada)")
        self.label_hex.setWordWrap(True)
        self.label_hex.setObjectName("statusLabel")
        layout.addWidget(self.label_hex)

        # ==================================================== LANGKAH 3: DEKRIPSI
        grup_dekripsi = QGroupBox("Langkah 3: Dekripsi & Simpan Kembali")
        h3 = QHBoxLayout(grup_dekripsi)
        self.btn_pilih_enc = QPushButton("Pilih .enc dari Tabel")
        self.btn_pilih_enc.clicked.connect(self._pilih_dari_tabel)
        self.btn_dekripsi = QPushButton("🔓 Dekripsi & Simpan sebagai PDF")
        self.btn_dekripsi.clicked.connect(self._dekripsi)
        h3.addWidget(self.btn_pilih_enc)
        h3.addWidget(self.btn_dekripsi)
        h3.addStretch()
        layout.addWidget(grup_dekripsi)

        # File .enc yang akan didekripsi (dipilih dari tabel atau dari file asli)
        self.path_enc: str | None = None
        self.label_enc = QLabel("Belum ada file .enc dipilih untuk didekripsi.")
        self.label_enc.setWordWrap(True)
        self.label_enc.setObjectName("statusLabel")
        layout.addWidget(self.label_enc)

        # ==================================================== DAFTAR FILE TERENKRIPSI
        grup_list = QGroupBox("Daftar File Terenkripsi (dari database)")
        vl = QVBoxLayout(grup_list)
        self.tabel_file = QTableWidget()
        self.tabel_file.setColumnCount(6)
        self.tabel_file.setHorizontalHeaderLabels(
            ["ID", "Nama File", "Ekstensi", "Ukuran (byte)", "Deskripsi", "Waktu"]
        )
        self.tabel_file.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabel_file.setAlternatingRowColors(True)
        self.tabel_file.setMaximumHeight(160)
        vl.addWidget(self.tabel_file)
        btn_refresh = QPushButton("Segarkan Daftar")
        btn_refresh.clicked.connect(self._refresh_tabel)
        vl.addWidget(btn_refresh)
        layout.addWidget(grup_list)

        layout.addStretch()

    # ------------------------------------------------------------ aksi
    def _cek_master_key(self) -> bool:
        if not session.is_authenticated or session.master_key is None:
            self._status("Belum login / Master Key tidak ada di memori.", "err")
            return False
        return True

    def _pilih_pdf(self) -> None:
        if not self._cek_master_key():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File PDF",
            "",
            "PDF (*.pdf)",
        )
        if path:
            self.path_pdf = path
            self.ekstensi = os.path.splitext(path)[1].lower()
            self.label_file.setText(
                f"File: {os.path.basename(path)}  [{self.ekstensi.upper()}]"
            )
            self._status("File PDF berhasil dipilih.", "ok")

    def _enkripsi(self) -> None:
        if not self.path_pdf or not os.path.isfile(self.path_pdf):
            self._status("Pilih file PDF terlebih dahulu.", "err")
            return
        if not self._cek_master_key():
            return
        try:
            (
                path_enc,
                nonce,
                size_asli,
                size_enc,
                ekstensi_asli,
            ) = cf.enkripsi_file(self.path_pdf, session.master_key)

            deskripsi = self.edit_deskripsi.text().strip()

            # Simpan metadata ke database (termasuk deskripsi).
            database = db_mod.Database()
            database.set_master_key(session.master_key)
            database.add_file_message(
                sender=session.username or "tidak diketahui",
                file_path=path_enc,
                nonce_hex=nonce.hex(),
                size=size_asli,
                deskripsi=deskripsi,
            )

            self.label_info.setText(
                "✅ Enkripsi berhasil!\n"
                f"File hasil: {os.path.basename(path_enc)}\n"
                f"Ekstensi: {ekstensi_asli.upper()}  |  Ukuran asli: {size_asli} byte  |  "
                f"Terenkripsi: {size_enc} byte"
            )
            self.label_hex.setText(
                f"Ciphertext (hex, awal): {cf.info_ciphertext_hex(path_enc)}..."
            )
            self._status(
                f"Enkripsi ChaCha20 berhasil ({ekstensi_asli.upper()}) & disimpan ke database.",
                "ok",
            )
            self._refresh_tabel()
        except Exception as exc:  # noqa: BLE001
            self._status(f"Gagal enkripsi: {exc}", "err")

    def _pilih_dari_tabel(self) -> None:
        """Pilih satu baris dari tabel file terenkripsi untuk didekripsi."""
        row = self.tabel_file.currentRow()
        if row < 0:
            self._status("Pilih satu baris pada tabel terlebih dahulu.", "err")
            return

        # Ambil nama file dari kolom index 1
        nama_file = self.tabel_file.item(row, 1).text()
        database = db_mod.Database()
        database.set_master_key(session.master_key)
        rows = database.get_file_messages(50)

        # Cari baris yang cocok berdasarkan nama file
        for r in rows:
            if os.path.basename(r["file_path"]) == nama_file:
                self.path_enc = r["file_path"]
                self.label_enc.setText(
                    f"File .enc untuk didekripsi: {os.path.basename(self.path_enc)}"
                )
                self._status(
                    "File .enc dipilih dari tabel. Klik 'Dekripsi & Simpan sebagai PDF'.",
                    "ok",
                )
                return

        self._status("File .enc tidak ditemukan di database.", "err")

    def _dekripsi(self) -> None:
        # Tentukan file .enc yang akan didekripsi: prioritas dari tabel (path_enc),
        # jika tidak ada gunakan file asli (path_pdf + .enc).
        path_enc = self.path_enc
        if path_enc is None and self.path_pdf and os.path.isfile(self.path_pdf):
            path_enc = self.path_pdf + ".enc"

        if not path_enc or not os.path.isfile(path_enc):
            self._status(
                "Pilih file .enc dari tabel terlebih dahulu (atau pilih file PDF asli).",
                "err",
            )
            return
        if not self._cek_master_key():
            return
        try:
            data_asli, ekstensi = cf.dekripsi_file(path_enc, session.master_key)

            # Nama default untuk menyimpan: hapus .enc dari nama file
            nama_default = os.path.basename(path_enc)
            if nama_default.endswith(".enc"):
                nama_default = nama_default[:-4]

            path_out, _ = QFileDialog.getSaveFileName(
                self,
                "Simpan Hasil Dekripsi",
                nama_default,
                f"File{ekstensi} (*{ekstensi})",
            )
            if not path_out:
                return
            if not path_out.lower().endswith(ekstensi):
                path_out += ekstensi

            with open(path_out, "wb") as f:
                f.write(data_asli)

            self._status(
                f"Dekripsi berhasil! Disimpan sebagai: {os.path.basename(path_out)}",
                "ok",
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Gagal Dekripsi", str(exc))
            self._status(f"Gagal: {exc}", "err")

    def _refresh_tabel(self) -> None:
        database = db_mod.Database()
        database.set_master_key(session.master_key)
        rows = database.get_file_messages(50)
        self.tabel_file.setRowCount(len(rows))
        for r, row in enumerate(rows):
            nama_file = os.path.basename(row["file_path"])
            ekstensi = os.path.splitext(nama_file)[1].upper()
            nilai = [
                str(row["id"]),
                nama_file,
                ekstensi,
                str(row["size"]),
                row["deskripsi"] or "-",
                row["created_at"],
            ]
            for c, v in enumerate(nilai):
                item = QTableWidgetItem(v)
                self.tabel_file.setItem(r, c, item)
        self.tabel_file.resizeColumnsToContents()

    def _status(self, teks: str, jenis: str = "") -> None:
        self.label_info.setText(teks)
