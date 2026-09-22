"""Review gallery: one card per photo, keep/discard checkbox, and entry points
into escalation, manual crop, and the detection detail view."""
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QGridLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

_EMPTY_STATE_TEXT = "No photos yet — choose a folder and click Process Folder to get started."
_EMPTY_STATE_WIDTH = 320
_LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "branding", "logo.png")
_LOGO_SIZE = 120

# Matches #photoCard's fixed min/max-width in the QSS.
_CARD_WIDTH = 248
_CARD_SPACING = 12


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

        self.crop_button = QPushButton("Manual Crop")
        self.crop_button.clicked.connect(lambda: self.manual_crop_requested.emit(self.job))

        self.details_button = QPushButton("Details")
        self.details_button.clicked.connect(lambda: self.details_requested.emit(self.job))

        layout = QVBoxLayout(self)
        layout.addWidget(self.thumb_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.keep_checkbox)
        layout.addWidget(self.escalate_checkbox)
        layout.addWidget(escalate_button)
        layout.addWidget(self.crop_button)
        layout.addWidget(self.details_button)

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

        is_preview = not self.job.processed
        self.keep_checkbox.setEnabled(not is_preview)
        self.crop_button.setEnabled(not is_preview)
        self.details_button.setEnabled(not is_preview)

        if self.job.error:
            self.status_label.setText(f"FAILED: {self.job.error}")
            self._set_status_state("failed")
            return
        if self.job.rendered is not None:
            self.thumb_label.setPixmap(_pil_to_pixmap(self.job.rendered))
        if is_preview:
            self.status_label.setText("not yet processed")
            self._set_status_state("preview")
            return
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

        self.cost_label = QLabel("This run: $0.000000 · Lifetime: $0.000000")
        self.cost_label.setObjectName("costLabel")
        self.cost_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.empty_label = QLabel(_EMPTY_STATE_TEXT)
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setWordWrap(True)
        # A genuinely fixed width (not just AlignHCenter) so Qt's
        # height-for-width wrapping is deterministic - a word-wrapped QLabel
        # centered via alignment alone sizes itself to an unreliable
        # "preferred width" heuristic, which previously clipped the last
        # line(s) of this message instead of reserving room for them.
        self.empty_label.setFixedWidth(_EMPTY_STATE_WIDTH)
        self.empty_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        self.logo_label = QLabel()
        self.logo_label.setObjectName("emptyStateLogo")
        logo_pixmap = QPixmap(_LOGO_PATH)
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(
                _LOGO_SIZE, _LOGO_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(logo_pixmap)
        self.logo_label.setAlignment(Qt.AlignCenter)

        # Centers the logo+message block within whatever leftover vertical
        # space the gallery has reserved (MainWindow's central layout always
        # gives the gallery stretch priority, populated or not) - a hidden
        # widget is excluded from its parent layout's space allocation
        # entirely, so only one of this wrapper / self._scroll ever actually
        # claims that space, matching whichever one is visible.
        self._empty_wrapper = QWidget()
        empty_wrapper_layout = QVBoxLayout(self._empty_wrapper)
        empty_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        empty_wrapper_layout.addStretch(1)
        empty_wrapper_layout.addWidget(self.logo_label, alignment=Qt.AlignHCenter)
        empty_wrapper_layout.addSpacing(16)
        empty_wrapper_layout.addWidget(self.empty_label, alignment=Qt.AlignHCenter)
        empty_wrapper_layout.addStretch(1)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._grid.setHorizontalSpacing(_CARD_SPACING)
        self._grid.setVerticalSpacing(_CARD_SPACING)
        self._scroll = QScrollArea()
        self._scroll.setWidget(self._container)
        self._scroll.setWidgetResizable(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.cost_label)
        layout.addWidget(self._empty_wrapper, stretch=1)
        layout.addWidget(self._scroll, stretch=1)

        self._update_empty_state()

    def refresh_cost(self):
        if self._decision_log is not None:
            this_run_cost = sum(
                getattr(card.job, "last_cost", None) or 0 for card in self.cards.values())
            self.cost_label.setText(
                f"This run: ${this_run_cost:.6f} · Lifetime: ${self._decision_log.running_cost:.6f}")

    def _column_count(self) -> int:
        # self.width() (not the scroll viewport's) so this reflects a
        # resize() immediately, even before the widget is shown and its
        # child layout has actually been activated - a plain scrollbar/
        # frame allowance stands in for the viewport's exact inner width.
        width = self.width() - 20
        cols = (width + _CARD_SPACING) // (_CARD_WIDTH + _CARD_SPACING)
        return max(1, int(cols))

    def add_job(self, job):
        card = PhotoCard(job)
        self.cards[job.src_path] = card
        row, col = divmod(self._next_index, self._column_count())
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
        cols = self._column_count()
        for card in self.cards.values():
            self._grid.removeWidget(card)
            row, col = divmod(self._next_index, cols)
            self._grid.addWidget(card, row, col)
            self._next_index += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow()

    def clear(self):
        for card in self.cards.values():
            self._grid.removeWidget(card)
            card.deleteLater()
        self.cards = {}
        self._next_index = 0
        self._update_empty_state()

    def _update_empty_state(self):
        self._empty_wrapper.setVisible(len(self.cards) == 0)
        self._scroll.setVisible(bool(self.cards))
