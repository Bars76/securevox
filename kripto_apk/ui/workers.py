"""ui/workers.py - Worker QThread untuk proses belakang SecureVox.

Semua proses berat dijalankan di thread terpisah agar jendela utama tidak
membeku. Hasil dikembalikan ke GUI thread melalui signal PySide6.

Worker yang tersedia:
    DongleWorker - polling deteksi dongle setiap interval (background thread).
"""
from __future__ import annotations

import time

import pythoncom
from PySide6.QtCore import QThread, Signal

import modules.dongle as dongle


class DongleWorker(QThread):
    """Polling dongle di background thread.

    Signals:
        status_changed(bool): emitted setiap kali status dongle berubah.
    """

    status_changed = Signal(bool)

    def __init__(self, interval_ms: int = 3000, parent=None) -> None:
        super().__init__(parent)
        self.interval_ms = max(500, interval_ms)
        self._running = True

    def run(self) -> None:
        # wmi/memakai COM -> harus diinisialisasi pada thread ini.
        pythoncom.CoInitialize()
        try:
            while self._running:
                online = dongle.cek_dongle()
                self.status_changed.emit(online)
                time.sleep(self.interval_ms / 1000.0)
        finally:
            pythoncom.CoUninitialize()

    def stop(self) -> None:
        self._running = False
        self.wait(2000)
