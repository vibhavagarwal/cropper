"""Dialog for entering/clearing the OpenAI API key, stored via the OS keyring
(src/api_key_store.py). No test API call on save - a bad key is discovered
the same way it is today, when the first real escalation call fails."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

import api_key_store as store


class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure API key")
        self._changed = False

        self.key_edit = QLineEdit(store.get_stored_key() or "")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("sk-...")

        clear_button = QPushButton("Clear stored key")
        clear_button.clicked.connect(self._on_clear_clicked)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save_clicked)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("OpenAI API key:"))
        layout.addWidget(self.key_edit)
        layout.addWidget(clear_button)
        layout.addWidget(buttons)

    def _on_save_clicked(self):
        value = self.key_edit.text().strip()
        if value:
            store.set_stored_key(value)
            self._changed = True
        self.accept()

    def _on_clear_clicked(self):
        store.clear_stored_key()
        self.key_edit.clear()
        self._changed = True
        self.accept()

    def key_changed(self) -> bool:
        return self._changed
