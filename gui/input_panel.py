"""Input panel: folder picker, drag-and-drop, and per-run controls (shape,
canvas size, filter on/off). Emits process_requested when the user starts a run."""
import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)


class InputPanel(QWidget):
    process_requested = Signal(str, str, int, bool)

    def __init__(self, initial_settings):
        super().__init__()
        self.setAcceptDrops(True)

        self.folder_edit = QLineEdit(initial_settings.last_input_folder)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._on_browse_clicked)

        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["square", "portrait", "landscape"])
        self.shape_combo.setCurrentText(initial_settings.shape)

        self.canvas_spin = QSpinBox()
        self.canvas_spin.setRange(200, 10000)
        self.canvas_spin.setValue(initial_settings.canvas_long)

        self.filter_checkbox = QCheckBox("Apply HP5 filter")
        self.filter_checkbox.setChecked(initial_settings.apply_filter)

        process_button = QPushButton("Process Folder")
        process_button.clicked.connect(self._on_process_clicked)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder:"))
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(browse_button)

        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel("Shape:"))
        controls_row.addWidget(self.shape_combo)
        controls_row.addWidget(QLabel("Canvas long edge:"))
        controls_row.addWidget(self.canvas_spin)
        controls_row.addWidget(self.filter_checkbox)
        controls_row.addWidget(process_button)

        layout = QVBoxLayout(self)
        layout.addLayout(folder_row)
        layout.addLayout(controls_row)

    def current_folder(self) -> str:
        return self.folder_edit.text()

    def _on_browse_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose input folder")
        if folder:
            self.folder_edit.setText(folder)

    def _on_process_clicked(self):
        self.process_requested.emit(
            self.folder_edit.text(),
            self.shape_combo.currentText(),
            self.canvas_spin.value(),
            self.filter_checkbox.isChecked(),
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.folder_edit.setText(path)
        event.acceptProposedAction()
