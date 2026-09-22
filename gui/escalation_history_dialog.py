"""Escalation history dialog: flat, newest-first list of every past
escalation from the DecisionLog. v1 is read-only - no filtering, sorting,
or export beyond Qt's free click-to-sort-by-column on the table headers."""
import time

from PySide6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QVBoxLayout

_COLUMNS = ["Photo", "Date/time", "Tier", "Provider", "Cost", "Confidence"]


class EscalationHistoryDialog(QDialog):
    def __init__(self, decision_log, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Escalation history")

        records = sorted(decision_log.records, key=lambda r: r.timestamp, reverse=True)

        self.table = QTableWidget(len(records), len(_COLUMNS))
        self.table.setHorizontalHeaderLabels(_COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        for row, record in enumerate(records):
            values = [
                record.photo_name,
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.timestamp)),
                record.tier,
                record.provider,
                f"${record.cost:.6f}",
                f"{record.confidence:.2f}",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        self.resize(700, 400)
