"""SecureVox - Aplikasi Pesan Aman Multimedia Berbasis USB Dongle.

Titik masuk aplikasi. Jalankan dengan:
    python main.py
"""
import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SecureVox")
    app.setOrganizationName("SecureVox")

    with open("ui/theme.qss", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
