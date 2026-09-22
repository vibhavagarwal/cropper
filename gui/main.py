"""Cropper desktop app entrypoint. Run with: python gui/main.py"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from main_window import MainWindow


_ICONS_DIR = (Path(__file__).resolve().parent / "assets" / "icons").as_posix()

_STYLESHEET_TEMPLATE = """
/* ---- surfaces ------------------------------------------------ */
QMainWindow, QDialog, QWidget {
    background: #16191d;
    color: #f0f3f6;
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
QWidget:disabled { color: #565d66; }
/* Labels must never paint their own background - otherwise every label
   sitting on a differently-colored container (a QGroupBox panel, a photo
   card, the empty-state box) shows a mismatched chip behind its text. */
QLabel { background: transparent; }
QToolTip { background: #21262d; color: #f0f3f6; border: 1px solid #30363d; padding: 4px 8px; }

/* ---- group box: keeps your structure, refines the look ------- */
QGroupBox {
    background: #21262d;
    border: 1px solid #30363d;
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
    color: #8b949e;
    background: #16191d;
}
QGroupBox QLabel, QGroupBox QCheckBox,
QGroupBox QComboBox, QGroupBox QSpinBox { font-weight: normal; }

/* ---- buttons ------------------------------------------------- */
QPushButton {
    background: #282e36;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px 12px;
    min-height: 20px;
    color: #f0f3f6;
}
QPushButton:hover    { background: #303742; border-color: #484f58; }
QPushButton:pressed  { background: #21262d; }
QPushButton:focus    { border-color: #388bfd; }
QPushButton:disabled { background: #21262d; border-color: #30363d; color: #565d66; }

QPushButton[primary="true"], QPushButton:default {
    background: #388bfd; border-color: #388bfd;
    color: #ffffff; font-weight: 600; padding: 5px 16px;
}
QPushButton[primary="true"]:hover, QPushButton:default:hover {
    background: #4a9eff; border-color: #4a9eff;
}
QPushButton[primary="true"]:pressed, QPushButton:default:pressed {
    background: #2a75e6; border-color: #2a75e6;
}
QPushButton[primary="true"]:disabled {
    background: #1e3a5f; border-color: #1e3a5f; color: #6e93bd;
}
QPushButton[quiet="true"] {
    background: transparent; border-color: transparent; color: #8b949e;
}
QPushButton[quiet="true"]:hover    { background: #21262d; border-color: #30363d; color: #f0f3f6; }
QPushButton[quiet="true"]:pressed  { background: #282e36; }
QPushButton[quiet="true"]:disabled { background: transparent; color: #565d66; }


/* ---- fields -------------------------------------------------- */
QLineEdit, QSpinBox, QComboBox {
    background: #1a1e24;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 20px;
    color: #f0f3f6;
    selection-background-color: #388bfd;
    selection-color: #ffffff;
}
QLineEdit:hover, QSpinBox:hover, QComboBox:hover { border-color: #484f58; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #388bfd; }
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background: #21262d; border-color: #30363d; color: #565d66;
}
QComboBox { padding-right: 24px; min-width: 96px; }
QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: center right;
    width: 22px; border: none;
}
QComboBox::down-arrow { image: url({A}/chevron-down.svg); width: 10px; height: 10px; }
QComboBox QAbstractItemView {
    background: #21262d; border: 1px solid #30363d; outline: 0; color: #f0f3f6;
    selection-background-color: #388bfd; selection-color: #ffffff;
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
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid #30363d; background: #1a1e24;
}
QCheckBox::indicator:hover   { border-color: #484f58; }
QCheckBox::indicator:checked { background: #388bfd; border-color: #388bfd; image: url({A}/check.svg); }
QCheckBox::indicator:disabled { background: #21262d; border-color: #30363d; }
QCheckBox::indicator:checked:disabled { background: #1e3a5f; border-color: #1e3a5f; }

/* ---- busy bar, status bar ------------------------------------ */
QProgressBar {
    max-height: 4px; border: none; border-radius: 2px;
    background: #21262d; qproperty-textVisible: false;
}
QProgressBar::chunk { background: #388bfd; border-radius: 2px; }
QStatusBar { background: transparent; color: #8b949e; border-top: 1px solid #30363d; }
QStatusBar::item { border: none; }

/* ---- table (escalation history) ------------------------------- */
QTableWidget {
    background: #16191d; alternate-background-color: #1a1e24;
    border: 1px solid #30363d; border-radius: 6px; gridline-color: #30363d;
    selection-background-color: #122d4d; selection-color: #f0f3f6;
}
QTableWidget::item { padding: 4px 6px; }
QHeaderView::section {
    background: #21262d; color: #8b949e; border: none;
    border-bottom: 1px solid #30363d; border-right: 1px solid #30363d;
    padding: 4px 6px; font-weight: 600;
}
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #30363d; border-radius: 3px; min-width: 28px; }
QScrollBar::handle:horizontal:hover { background: #484f58; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QScrollBar::corner { background: #16191d; }

/* ---- gallery ------------------------------------------------- */
QScrollArea {
    background: #16191d; border: 1px solid #30363d; border-radius: 6px;
}
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #30363d; border-radius: 3px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #484f58; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

#costLabel {
    color: #8b949e; font-size: 8pt;
    qproperty-alignment: 'AlignRight | AlignVCenter';
}
#emptyState {
    background: #21262d; border: 1px dashed #30363d; border-radius: 8px;
    color: #8b949e; font-size: 10pt; padding: 48px;
    qproperty-alignment: AlignCenter;
}


/* ---- photo card ---------------------------------------------- */
#photoCard {
    background: #21262d; border: 1px solid #30363d; border-radius: 8px;
    min-width: 248px; max-width: 248px;
}
#photoCard[kept="true"] { background: #1a2740; border-color: #388bfd; }
#photoCard QPushButton  { padding: 3px 10px; min-height: 18px; }
#photoThumb {
    background: #1a1e24; border-radius: 4px; padding: 4px;
    qproperty-alignment: AlignCenter;
}
#keepCheck { font-weight: 600; }
#escalateCheck { color: #8b949e; font-size: 8pt; }
#escalateCheck:disabled { color: #565d66; }

#photoStatus {
    background: #282e36; color: #8b949e; border-radius: 4px;
    padding: 5px 8px; font-size: 8pt; min-height: 26px;
}
#photoStatus[state="flagged"]   { background: #382c0e; color: #e3b341; }
#photoStatus[state="escalated"] { background: #122d4d; color: #58a6ff; }
#photoStatus[state="failed"]    { background: #3d1418; color: #f85149; }
#photoStatus[state="preview"]   { background: #282e36; color: #6b727b; font-style: italic; }
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
