"""Confirmation gate shown before any paid escalation call: a worst-case cost
estimate (every flagged photo assumed to need the strong tier), approved
explicitly before spend happens."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import QDialogButtonBox, QLabel, QVBoxLayout, QDialog

from cost import estimate_worst_case_batch_cost


class EscalationConfirmDialog(QDialog):
    def __init__(self, provider, num_photos: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm AI escalation")
        self._confirmed = False

        worst_case = estimate_worst_case_batch_cost(provider, num_photos)
        self.cost_label = QLabel(
            f"Escalating {num_photos} photo(s) could cost up to ${worst_case:.4f} "
            "(worst case, assumes every photo needs the stronger tier)."
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Escalate")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.cost_label)
        layout.addWidget(buttons)

    def _on_accept(self):
        self._confirmed = True
        self.accept()

    def confirmed(self) -> bool:
        return self._confirmed
