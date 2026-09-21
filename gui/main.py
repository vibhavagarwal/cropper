"""Cropper desktop app entrypoint. Run with: python gui/main.py"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from main_window import MainWindow


_ICONS_DIR = (Path(__file__).resolve().parent / "assets" / "icons").as_posix()

_STYLESHEET_TEMPLATE = """
/* ---- surfaces ------------------------------------------------ */
QMainWindow, QDialog { background: #f5f6f8; }
QWidget:disabled { color: #a0a7b3; }
QToolTip { background: #1f2430; color: #ffffff; border: none; padding: 4px 8px; }

/* ---- group box: keeps your structure, refines the look ------- */
QGroupBox {
    background: #ffffff;
    border: 1px solid #dde1e8;
    border-radius: 6px;
    margin-top: 10px;
    padding: 14px 12px 10px 12px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: #5b6472;
    background: #f5f6f8;
}
QGroupBox QLabel, QGroupBox QCheckBox,
QGroupBox QComboBox, QGroupBox QSpinBox { font-weight: normal; }

/* ---- buttons ------------------------------------------------- */
QPushButton {
    background: #ffffff;
    border: 1px solid #b4bbc7;
    border-radius: 4px;
    padding: 4px 12px;
    min-height: 20px;
}
QPushButton:hover    { background: #f1f3f7; border-color: #8792a4; }
QPushButton:pressed  { background: #e4e7ee; }
QPushButton:focus    { border-color: #2f6fed; }
QPushButton:disabled { background: #f5f6f8; border-color: #e3e6ec; color: #a0a7b3; }

QPushButton[primary="true"], QPushButton:default {
    background: #2f6fed; border-color: #2f6fed;
    color: #ffffff; font-weight: 600; padding: 5px 16px;
}
QPushButton[primary="true"]:hover, QPushButton:default:hover {
    background: #255ac7; border-color: #255ac7;
}
QPushButton[primary="true"]:pressed, QPushButton:default:pressed {
    background: #1f4ba6; border-color: #1f4ba6;
}
QPushButton[primary="true"]:disabled {
    background: #a9c1f4; border-color: #a9c1f4; color: #f4f7fe;
}
QPushButton[quiet="true"] {
    background: transparent; border-color: transparent; color: #4a5565;
}
QPushButton[quiet="true"]:hover    { background: #e6e9ef; }
QPushButton[quiet="true"]:pressed  { background: #dbdfe7; }
QPushButton[quiet="true"]:disabled { background: transparent; color: #a0a7b3; }


/* ---- fields -------------------------------------------------- */
QLineEdit, QSpinBox, QComboBox {
    background: #ffffff;
    border: 1px solid #b4bbc7;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 20px;
    selection-background-color: #2f6fed;
    selection-color: #ffffff;
}
QLineEdit:hover, QSpinBox:hover, QComboBox:hover { border-color: #8792a4; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #2f6fed; }
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background: #f5f6f8; border-color: #e3e6ec; color: #a0a7b3;
}
QComboBox { padding-right: 24px; min-width: 96px; }
QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: center right;
    width: 22px; border: none;
}
QComboBox::down-arrow { image: url({A}/chevron-down.svg); width: 10px; height: 10px; }
QComboBox QAbstractItemView {
    background: #ffffff; border: 1px solid #b4bbc7; outline: 0;
    selection-background-color: #e8effd; selection-color: #1f2430;
}
QSpinBox { padding-right: 22px; }
QSpinBox::up-button, QSpinBox::down-button {
    subcontrol-origin: border; width: 18px; border: none; background: transparent;
}
QSpinBox::up-button   { subcontrol-position: top right; }
QSpinBox::down-button { subcontrol-position: bottom right; }
QSpinBox::up-arrow   { image: url({A}/chevron-up.svg);   width: 8px; height: 8px; }
QSpinBox::down-arrow { image: url({A}/chevron-down.svg); width: 8px; height: 8px; }

/* ---- checkbox ------------------------------------------------ */
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 3px;
    border: 1px solid #7f8a9b; background: #ffffff;
}
QCheckBox::indicator:hover   { border-color: #2f6fed; }
QCheckBox::indicator:checked { background: #2f6fed; border-color: #2f6fed; image: url({A}/check.svg); }
QCheckBox::indicator:disabled { background: #f5f6f8; border-color: #d5d9e0; }
QCheckBox::indicator:checked:disabled { background: #c5d5f8; border-color: #c5d5f8; }

/* ---- busy bar, status bar ------------------------------------ */
QProgressBar {
    max-height: 4px; border: none; border-radius: 2px;
    background: #dfe3ea; qproperty-textVisible: false;
}
QProgressBar::chunk { background: #2f6fed; border-radius: 2px; }
QStatusBar { background: transparent; color: #5b6472; border-top: 1px solid #e1e4ea; }
QStatusBar::item { border: none; }

/* ---- gallery ------------------------------------------------- */
QScrollArea {
    background: #eceef2; border: 1px solid #dde1e8; border-radius: 6px;
}
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #c5cad3; border-radius: 3px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #a9b0bd; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

#costLabel {
    color: #5b6472; font-size: 8pt;
    qproperty-alignment: 'AlignRight | AlignVCenter';
}
#emptyState {
    background: #eceef2; border: 1px dashed #c0c6d1; border-radius: 8px;
    color: #5b6472; font-size: 10pt; padding: 48px;
    qproperty-alignment: AlignCenter;
}


/* ---- photo card ---------------------------------------------- */
#photoCard {
    background: #ffffff; border: 1px solid #dde1e8; border-radius: 6px;
    min-width: 248px; max-width: 248px;
}
#photoCard[kept="true"] { background: #f4f8ff; border-color: #2f6fed; }
#photoCard QPushButton  { padding: 3px 10px; min-height: 18px; }
#photoThumb {
    background: #eceef2; border-radius: 4px; padding: 4px;
    qproperty-alignment: AlignCenter;
}
#keepCheck { font-weight: 600; }
#escalateCheck { color: #5b6472; font-size: 8pt; }
#escalateCheck:disabled { color: #a0a7b3; }

#photoStatus {
    background: #f0f2f5; color: #5b6472; border-radius: 4px;
    padding: 5px 8px; font-size: 8pt; min-height: 26px;
}
#photoStatus[state="flagged"]   { background: #fff4d6; color: #7a5200; }
#photoStatus[state="escalated"] { background: #e6effe; color: #1c4fb8; }
#photoStatus[state="failed"]    { background: #fdecec; color: #a61b1b; }
"""

_STYLESHEET = _STYLESHEET_TEMPLATE.replace("{A}", _ICONS_DIR)


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
