"""Review gallery: one card per photo, keep/discard checkbox, and entry points
into escalation, manual crop, and the detection detail view."""
from PySide6.QtCore import Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)


def _pil_to_pixmap(pil_image, max_size=220):
    thumb = pil_image.copy()
    thumb.thumbnail((max_size, max_size))
    thumb = thumb.convert("RGB")
    qimage = QImage(thumb.tobytes(), thumb.width, thumb.height,
                     thumb.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage)


class PhotoCard(QWidget):
    escalate_requested = Signal(object)
    manual_crop_requested = Signal(object)
    details_requested = Signal(object)

    def __init__(self, job):
        super().__init__()
        self.job = job

        self.thumb_label = QLabel()
        self.status_label = QLabel()
        self.keep_checkbox = QCheckBox("Keep")
        self.keep_checkbox.toggled.connect(self._on_keep_toggled)

        escalate_button = QPushButton("Escalate")
        escalate_button.setEnabled(bool(job.triage_decision and job.triage_decision.escalate))
        escalate_button.clicked.connect(self._on_escalate_clicked)

        crop_button = QPushButton("Manual Crop")
        crop_button.clicked.connect(lambda: self.manual_crop_requested.emit(self.job))

        details_button = QPushButton("Details")
        details_button.clicked.connect(lambda: self.details_requested.emit(self.job))

        layout = QVBoxLayout(self)
        layout.addWidget(self.thumb_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.keep_checkbox)
        layout.addWidget(escalate_button)
        layout.addWidget(crop_button)
        layout.addWidget(details_button)

        self._refresh_visuals()

    def _on_keep_toggled(self, checked):
        self.job.keep = checked

    def _on_escalate_clicked(self):
        self.escalate_requested.emit(self.job)

    def update_job(self, job):
        self.job = job
        self._refresh_visuals()

    def _refresh_visuals(self):
        if self.job.error:
            self.status_label.setText(f"FAILED: {self.job.error}")
            return
        if self.job.rendered is not None:
            self.thumb_label.setPixmap(_pil_to_pixmap(self.job.rendered))
        if self.job.crop_decision is not None:
            self.status_label.setText(
                f"escalated ({self.job.crop_decision.tier}, "
                f"confidence {self.job.crop_decision.confidence:.2f})"
            )
        elif self.job.triage_decision and self.job.triage_decision.escalate:
            self.status_label.setText("flagged for escalation")
        else:
            self.status_label.setText("formula crop")


class ReviewGallery(QScrollArea):
    def __init__(self):
        super().__init__()
        self.cards = {}
        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self._next_index = 0

    def add_job(self, job):
        card = PhotoCard(job)
        self.cards[job.src_path] = card
        row, col = divmod(self._next_index, 4)
        self._grid.addWidget(card, row, col)
        self._next_index += 1

    def update_job(self, job):
        card = self.cards.get(job.src_path)
        if card is not None:
            card.update_job(job)

    def kept_jobs(self):
        return [card.job for card in self.cards.values() if card.keep_checkbox.isChecked()]

    def clear(self):
        for card in self.cards.values():
            self._grid.removeWidget(card)
            card.deleteLater()
        self.cards = {}
        self._next_index = 0
