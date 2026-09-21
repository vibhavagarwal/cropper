"""Review gallery: one card per photo, keep/discard checkbox, and entry points
into escalation, manual crop, and the detection detail view."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

_EMPTY_STATE_TEXT = "No photos yet — choose a folder and click Process Folder to get started."


def _pil_to_pixmap(pil_image, max_size=220):
    thumb = pil_image.copy()
    thumb.thumbnail((max_size, max_size))
    thumb = thumb.convert("RGB")
    qimage = QImage(thumb.tobytes(), thumb.width, thumb.height,
                     thumb.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage)


def _escalation_eligible(job) -> bool:
    return bool(job.triage_decision and job.triage_decision.escalate) and job.crop_decision is None


class PhotoCard(QWidget):
    escalate_requested = Signal(object)
    manual_crop_requested = Signal(object)
    details_requested = Signal(object)
    escalate_selection_changed = Signal()
    keep_selection_changed = Signal()

    def __init__(self, job):
        super().__init__()
        self.job = job
        self.setObjectName("photoCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.thumb_label = QLabel()
        self.thumb_label.setObjectName("photoThumb")
        self.status_label = QLabel()
        self.status_label.setObjectName("photoStatus")
        self.status_label.setWordWrap(True)
        self.keep_checkbox = QCheckBox("Keep")
        self.keep_checkbox.setObjectName("keepCheck")
        self.keep_checkbox.toggled.connect(self._on_keep_toggled)

        escalate_button = QPushButton("Escalate")
        escalate_button.setEnabled(_escalation_eligible(job))
        escalate_button.clicked.connect(self._on_escalate_clicked)

        self.escalate_checkbox = QCheckBox("Select for escalation")
        self.escalate_checkbox.setObjectName("escalateCheck")
        self.escalate_checkbox.setEnabled(_escalation_eligible(job))
        self.escalate_checkbox.toggled.connect(lambda _checked: self.escalate_selection_changed.emit())

        crop_button = QPushButton("Manual Crop")
        crop_button.clicked.connect(lambda: self.manual_crop_requested.emit(self.job))

        details_button = QPushButton("Details")
        details_button.clicked.connect(lambda: self.details_requested.emit(self.job))

        layout = QVBoxLayout(self)
        layout.addWidget(self.thumb_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.keep_checkbox)
        layout.addWidget(self.escalate_checkbox)
        layout.addWidget(escalate_button)
        layout.addWidget(crop_button)
        layout.addWidget(details_button)

        self._refresh_visuals()

    def _on_keep_toggled(self, checked):
        self.job.keep = checked
        self.setProperty("kept", checked)
        self.style().unpolish(self)
        self.style().polish(self)
        self.keep_selection_changed.emit()

    def _on_escalate_clicked(self):
        self.escalate_requested.emit(self.job)

    def update_job(self, job):
        self.job = job
        self._refresh_visuals()

    def _refresh_visuals(self):
        eligible = _escalation_eligible(self.job)
        self.escalate_checkbox.setEnabled(eligible)
        if not eligible and self.escalate_checkbox.isChecked():
            self.escalate_checkbox.setChecked(False)
        if self.job.error:
            self.status_label.setText(f"FAILED: {self.job.error}")
            self._set_status_state("failed")
            return
        if self.job.rendered is not None:
            self.thumb_label.setPixmap(_pil_to_pixmap(self.job.rendered))
        if self.job.crop_decision is not None:
            cost = getattr(self.job, "last_cost", None)
            cost_suffix = f", ${cost:.6f}" if cost is not None else ""
            self.status_label.setText(
                f"escalated ({self.job.crop_decision.tier}, "
                f"confidence {self.job.crop_decision.confidence:.2f}{cost_suffix})"
            )
            self._set_status_state("escalated")
        elif self.job.triage_decision and self.job.triage_decision.escalate:
            self.status_label.setText("flagged for escalation")
            self._set_status_state("flagged")
        else:
            self.status_label.setText("formula crop")

    def _set_status_state(self, state):
        self.status_label.setProperty("state", state)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)


class ReviewGallery(QWidget):
    def __init__(self, decision_log=None):
        super().__init__()
        self.cards = {}
        self._decision_log = decision_log
        self._next_index = 0

        self.cost_label = QLabel("Running cost: $0.000000")
        self.cost_label.setObjectName("costLabel")
        self.empty_label = QLabel(_EMPTY_STATE_TEXT)
        self.empty_label.setObjectName("emptyState")

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._scroll = QScrollArea()
        self._scroll.setWidget(self._container)
        self._scroll.setWidgetResizable(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.cost_label)
        layout.addWidget(self.empty_label)
        layout.addWidget(self._scroll)

        self._update_empty_state()

    def refresh_cost(self):
        if self._decision_log is not None:
            self.cost_label.setText(f"Running cost: ${self._decision_log.running_cost:.6f}")

    def add_job(self, job):
        card = PhotoCard(job)
        self.cards[job.src_path] = card
        row, col = divmod(self._next_index, 4)
        self._grid.addWidget(card, row, col)
        self._next_index += 1
        self._update_empty_state()

    def update_job(self, job):
        card = self.cards.get(job.src_path)
        if card is not None:
            card.update_job(job)

    def kept_jobs(self):
        return [card.job for card in self.cards.values() if card.keep_checkbox.isChecked()]

    def has_unsaved_kept_work(self) -> bool:
        return any(card.keep_checkbox.isChecked() for card in self.cards.values())

    def selected_for_escalation(self):
        return [card.job for card in self.cards.values() if card.escalate_checkbox.isChecked()]

    def remove_job(self, src_path):
        card = self.cards.pop(src_path, None)
        if card is not None:
            self._grid.removeWidget(card)
            card.deleteLater()
            self._reflow()
        self._update_empty_state()

    def _reflow(self):
        self._next_index = 0
        for card in self.cards.values():
            self._grid.removeWidget(card)
            row, col = divmod(self._next_index, 4)
            self._grid.addWidget(card, row, col)
            self._next_index += 1

    def clear(self):
        for card in self.cards.values():
            self._grid.removeWidget(card)
            card.deleteLater()
        self.cards = {}
        self._next_index = 0
        self._update_empty_state()

    def _update_empty_state(self):
        self.empty_label.setVisible(len(self.cards) == 0)
        self._scroll.setVisible(bool(self.cards))
