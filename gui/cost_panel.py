"""Running cost total and per-photo decision history, visible in-app rather
than only in the background log file."""
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget


class CostPanel(QWidget):
    def __init__(self, decision_log):
        super().__init__()
        self.decision_log = decision_log
        self.total_label = QLabel("Running cost: $0.000000")
        self.history_list = QListWidget()

        layout = QVBoxLayout(self)
        layout.addWidget(self.total_label)
        layout.addWidget(self.history_list)

        self.refresh()

    def refresh(self) -> None:
        self.total_label.setText(f"Running cost: ${self.decision_log.running_cost:.6f}")
        self.history_list.clear()
        for record in self.decision_log.records:
            if record.escalated:
                text = (f"{record.photo_name}: {record.provider}/{record.tier}, "
                        f"confidence {record.confidence:.2f}, ${record.cost:.6f}")
            else:
                text = f"{record.photo_name}: not escalated"
            self.history_list.addItem(text)
