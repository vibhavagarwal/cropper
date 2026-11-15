"""Input panel: folder picker, drag-and-drop, and per-run controls (shape,
canvas size, filter on/off). Emits process_requested when the user starts a run."""
import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)


LOOK_LABELS = {"none": "None", "bw": "B&W (HP5)", "moodportrait": "MoodPortrait"}


class InputPanel(QWidget):
    process_requested = Signal(str, str, int, bool, bool, str, str, str)
    stop_requested = Signal()
    folder_selected = Signal(str)

    def __init__(self, initial_settings):
        super().__init__()
        self.setAcceptDrops(True)
        self._is_processing = False

        self.folder_edit = QLineEdit(initial_settings.last_input_folder)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._on_browse_clicked)

        self.load_button = QPushButton("Load folder")
        self.load_button.clicked.connect(self._on_load_folder_clicked)

        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["square", "portrait", "landscape"])
        self.shape_combo.setCurrentText(initial_settings.shape)

        self.canvas_spin = QSpinBox()
        self.canvas_spin.setRange(200, 10000)
        self.canvas_spin.setValue(initial_settings.canvas_long)

        # Look replaces the old "Apply B/W filter" checkbox: the looks cannot be combined (MoodPortrait is colour).
        self.look_combo = QComboBox()
        for value, label in LOOK_LABELS.items():
            self.look_combo.addItem(label, value)
        look = initial_settings.look or ("bw" if initial_settings.apply_bw else "none")
        self.look_combo.setCurrentIndex(max(0, self.look_combo.findData(look)))

        self.grain_checkbox = QCheckBox("Apply grain")
        self.grain_checkbox.setChecked(initial_settings.apply_grain)

        self.grain_size_combo = QComboBox()
        self.grain_size_combo.addItems(["small", "medium", "large"])
        self.grain_size_combo.setCurrentText(initial_settings.grain_size)

        self.border_size_combo = QComboBox()
        self.border_size_combo.addItems(["small", "medium", "large"])
        self.border_size_combo.setCurrentText(initial_settings.border_size)

        self.process_button = QPushButton("Process Folder")
        self.process_button.setProperty("primary", True)
        self.process_button.clicked.connect(self._on_process_button_clicked)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder:"))
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(self.browse_button)
        folder_row.addWidget(self.load_button)
        folder_row.addWidget(self.process_button)

        self.settings_group = QGroupBox("Run settings")
        # Two rows rather than one long one - a single QHBoxLayout with this
        # many widgets has no way to wrap, so at narrow window widths the
        # labels/controls get squeezed below their natural size and overlap
        # instead of reflowing.
        settings_row = QHBoxLayout()
        settings_row.addWidget(QLabel("Shape:"))
        settings_row.addWidget(self.shape_combo)
        settings_row.addSpacing(12)
        settings_row.addWidget(QLabel("Canvas long edge:"))
        settings_row.addWidget(self.canvas_spin)
        settings_row.addStretch()

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Look:"))
        filter_row.addWidget(self.look_combo)
        filter_row.addWidget(self.grain_checkbox)
        filter_row.addWidget(QLabel("Grain size:"))
        filter_row.addWidget(self.grain_size_combo)
        filter_row.addWidget(QLabel("Border size:"))
        filter_row.addWidget(self.border_size_combo)
        filter_row.addStretch()

        settings_group_layout = QVBoxLayout(self.settings_group)
        settings_group_layout.addLayout(settings_row)
        settings_group_layout.addLayout(filter_row)

        layout = QVBoxLayout(self)
        layout.addLayout(folder_row)
        layout.addWidget(self.settings_group)

    def current_folder(self) -> str:
        return self.folder_edit.text()

    def _on_browse_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose input folder")
        if folder:
            self.folder_edit.setText(folder)
            self.folder_selected.emit(folder)

    def _on_load_folder_clicked(self):
        folder = self.folder_edit.text()
        if folder:
            self.folder_selected.emit(folder)

    def _on_process_button_clicked(self):
        if self._is_processing:
            self.stop_requested.emit()
            return
        self.process_requested.emit(
            self.folder_edit.text(),
            self.shape_combo.currentText(),
            self.canvas_spin.value(),
            self.look_combo.currentData() == "bw",
            self.grain_checkbox.isChecked(),
            self.grain_size_combo.currentText(),
            self.border_size_combo.currentText(),
            self.look_combo.currentData(),
        )

    def set_processing(self, is_processing: bool):
        self._is_processing = is_processing
        self.process_button.setText("Stop" if is_processing else "Process Folder")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.folder_edit.setText(path)
                self.folder_selected.emit(path)
        event.acceptProposedAction()
