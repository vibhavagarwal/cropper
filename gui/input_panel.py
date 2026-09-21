"""Input panel: folder picker, drag-and-drop, and per-run controls (shape,
canvas size, filter on/off). Emits process_requested when the user starts a run."""
import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)


class InputPanel(QWidget):
    process_requested = Signal(str, str, int, bool, bool, str)

    def __init__(self, initial_settings):
        super().__init__()
        self.setAcceptDrops(True)

        self.folder_edit = QLineEdit(initial_settings.last_input_folder)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._on_browse_clicked)

        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["square", "portrait", "landscape"])
        self.shape_combo.setCurrentText(initial_settings.shape)

        self.canvas_spin = QSpinBox()
        self.canvas_spin.setRange(200, 10000)
        self.canvas_spin.setValue(initial_settings.canvas_long)

        self.bw_checkbox = QCheckBox("Apply B/W filter")
        self.bw_checkbox.setChecked(initial_settings.apply_bw)

        self.grain_checkbox = QCheckBox("Apply grain")
        self.grain_checkbox.setChecked(initial_settings.apply_grain)

        self.grain_size_combo = QComboBox()
        self.grain_size_combo.addItems(["small", "medium", "large"])
        self.grain_size_combo.setCurrentText(initial_settings.grain_size)

        self.process_button = QPushButton("Process Folder")
        self.process_button.setProperty("primary", True)
        self.process_button.clicked.connect(self._on_process_clicked)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder:"))
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(self.browse_button)

        self.settings_group = QGroupBox("Run settings")
        settings_row = QHBoxLayout(self.settings_group)
        settings_row.addWidget(QLabel("Shape:"))
        settings_row.addWidget(self.shape_combo)
        settings_row.addWidget(QLabel("Canvas long edge:"))
        settings_row.addWidget(self.canvas_spin)
        settings_row.addWidget(self.bw_checkbox)
        settings_row.addWidget(self.grain_checkbox)
        settings_row.addWidget(QLabel("Grain size:"))
        settings_row.addWidget(self.grain_size_combo)

        process_row = QHBoxLayout()
        process_row.addStretch()
        process_row.addWidget(self.process_button)

        layout = QVBoxLayout(self)
        layout.addLayout(folder_row)
        layout.addWidget(self.settings_group)
        layout.addLayout(process_row)

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
            self.bw_checkbox.isChecked(),
            self.grain_checkbox.isChecked(),
            self.grain_size_combo.currentText(),
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
