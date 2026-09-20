"""Cropper desktop app entrypoint. Run with: python gui/main.py"""
import sys

from PySide6.QtWidgets import QApplication

from main_window import MainWindow


_STYLESHEET = """
QGroupBox {
    margin-top: 10px;
    padding-top: 10px;
    border: 1px solid #c0c0c0;
    border-radius: 4px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #555555;
}
QPushButton[primary="true"] {
    background-color: #2f6fed;
    color: white;
    font-weight: bold;
    padding: 6px 16px;
    border-radius: 4px;
}
QPushButton[primary="true"]:hover {
    background-color: #255ac7;
}
QPushButton {
    padding: 4px 10px;
}
"""


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(_STYLESHEET)
    window = MainWindow()
    window.resize(1100, 750)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.path.insert(0, ".")
    sys.exit(main())
