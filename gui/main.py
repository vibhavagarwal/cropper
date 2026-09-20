"""Cropper desktop app entrypoint. Run with: python gui/main.py"""
import sys

from PySide6.QtWidgets import QApplication

from main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1100, 750)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.path.insert(0, ".")
    sys.exit(main())
