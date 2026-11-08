"""ui/tabs/log_tab.py - Tab Log Aktivitas."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import modules.database as db_mod


class LogTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.btn_refresh = QPushButton("Segarkan Log")
        self.btn_refresh.clicked.connect(self._refresh)
        layout.addWidget(self.btn_refresh)

        self.tabel = QTableWidget()
        self.tabel.setColumnCount(4)
        self.tabel.setHorizontalHeaderLabels(["ID", "Event", "Status", "Waktu"])
        self.tabel.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabel.setAlternatingRowColors(True)
        layout.addWidget(self.tabel)

        self._refresh()

    def _refresh(self) -> None:
        database = db_mod.Database()
        rows = database.get_logs(100)
        self.tabel.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, kunci in enumerate(["id", "event", "status", "created_at"]):
                item = QTableWidgetItem(str(row[kunci]))
                self.tabel.setItem(r, c, item)
        self.tabel.resizeColumnsToContents()
