"""Main window: wires the input panel, background workers, review gallery,
escalation flow, cost panel, and save action together."""
import sys
import time
from pathlib import Path

# Two path inserts: "src" for the engine modules below, and this file's own
# directory (gui/) so the bare sibling imports below (cost_panel,
# crop_editor_dialog, etc.) resolve even when this module is loaded as
# gui.main_window (e.g. from tests) rather than run as a top-level script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

from settings import AppSettings
from decision_log import DecisionLog, DecisionRecord
from providers.openai_provider import OpenAICropProvider
import hp5_emulate as H
import pipeline as P

from api_key_dialog import ApiKeyDialog
from crop_editor_dialog import CropEditorDialog
from detail_view_dialog import DetailViewDialog
from escalation_dialog import EscalationConfirmDialog
from input_panel import InputPanel
from review_gallery import ReviewGallery
from save_action import expected_output_path, save_kept_jobs
from workers import EscalationWorker, ProcessFolderWorker

# Below this confidence, the cheap-tier result auto-escalates to the strong
# tier. Fully automatic per the Global Constraints - no manual override.
AUTO_ESCALATE_CONFIDENCE_THRESHOLD = 0.6


class MainWindow(QMainWindow):
    def __init__(self, settings_path: Path = None, decision_log_path: Path = None):
        super().__init__()
        self.setWindowTitle("Cropper")
        self.setMinimumSize(900, 600)

        self.settings_path = settings_path or (Path.home() / ".cropper" / "settings.json")
        self.settings = AppSettings.load(self.settings_path)

        self.decision_log_path = decision_log_path or (Path.home() / ".cropper" / "decision_log.jsonl")
        self.decision_log = DecisionLog(self.decision_log_path)

        self.provider = None
        self._reload_provider()
        self._output_override = None
        self._worker = None

        self.input_panel = InputPanel(self.settings)
        self.input_panel.process_requested.connect(self._start_processing)

        self.gallery = ReviewGallery(decision_log=self.decision_log)

        self.busy_indicator = QProgressBar()
        self.busy_indicator.setRange(0, 0)
        self.busy_indicator.hide()

        self.save_button = QPushButton("Save Selected")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._on_save_clicked)
        choose_output_button = QPushButton("Choose output folder...")
        choose_output_button.clicked.connect(self._on_choose_output_clicked)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._on_clear_clicked)
        self.escalate_selected_button = QPushButton("Escalate selected")
        self.escalate_selected_button.setEnabled(False)
        self.escalate_selected_button.clicked.connect(self._on_escalate_selected_clicked)
        self.configure_api_key_button = QPushButton("Configure API key...")
        self.configure_api_key_button.clicked.connect(self._on_configure_api_key_clicked)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.save_button)
        bottom_row.addWidget(self.escalate_selected_button)
        bottom_row.addWidget(choose_output_button)
        bottom_row.addWidget(self.clear_button)
        bottom_row.addWidget(self.configure_api_key_button)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.input_panel)
        layout.addWidget(self.busy_indicator)
        layout.addWidget(self.gallery)
        layout.addLayout(bottom_row)
        self.setCentralWidget(central)

    def _set_busy(self, is_busy: bool):
        self.busy_indicator.setVisible(is_busy)

    def _reload_provider(self):
        try:
            self.provider = OpenAICropProvider()
        except Exception:
            self.provider = None

    def _on_configure_api_key_clicked(self):
        dialog = ApiKeyDialog(parent=self)
        dialog.exec()
        if dialog.key_changed():
            self._reload_provider()

    def output_folder(self) -> str:
        if self._output_override:
            return self._output_override
        return self.input_panel.current_folder().rstrip("/\\") + "/out"

    def _on_choose_output_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if folder:
            self._output_override = folder

    def _start_processing(self, folder, shape, canvas_long, apply_filter):
        if self._worker is not None and self._worker.isRunning():
            self.statusBar().showMessage("Already processing a folder — please wait for it to finish.", 5000)
            return
        if self.gallery.has_unsaved_kept_work():
            answer = QMessageBox.question(
                self, "Discard unsaved work?",
                "Some kept photos haven't been saved yet. Starting a new run will discard "
                "them. Continue?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.gallery.clear()
        self._update_save_button()
        # Keep the input panel's folder field authoritative for output_folder()
        # even when a caller (e.g. a test, or a future re-run action) invokes
        # this directly instead of going through the panel's own signal.
        self.input_panel.folder_edit.setText(folder)

        self.settings.shape = shape
        self.settings.canvas_long = canvas_long
        self.settings.apply_filter = apply_filter
        self.settings.last_input_folder = folder
        self.settings.save(self.settings_path)

        self._set_busy(True)
        self._worker = ProcessFolderWorker(folder, shape, canvas_long, apply_filter)
        self._worker.photo_ready.connect(self._on_photo_ready)
        self._worker.finished_all.connect(self._on_processing_finished)
        self._worker.start()

    def _on_processing_finished(self):
        self._set_busy(False)
        self.statusBar().showMessage("Processing complete.", 3000)

    def _on_photo_ready(self, job):
        self.gallery.add_job(job)
        card = self.gallery.cards[job.src_path]
        card.escalate_requested.connect(self._on_escalate_requested)
        card.manual_crop_requested.connect(self._on_manual_crop_requested)
        card.details_requested.connect(self._on_details_requested)
        card.escalate_selection_changed.connect(self._update_escalate_selected_button)
        card.keep_selection_changed.connect(self._update_save_button)

    def _update_escalate_selected_button(self):
        self.escalate_selected_button.setEnabled(bool(self.gallery.selected_for_escalation()))

    def _update_save_button(self):
        self.save_button.setEnabled(bool(self.gallery.kept_jobs()))

    def _on_escalate_requested(self, job):
        if self.provider is None:
            self.statusBar().showMessage(
                "Escalation unavailable: no OpenAI API key configured (set OPENAI_API_KEY).", 5000)
            return
        confirm = EscalationConfirmDialog(self.provider, num_photos=1, parent=self)
        confirm.exec()
        if not confirm.confirmed():
            return
        self._run_escalation_worker(job, "cheap")

    def _run_escalation_worker(self, job, tier, error_handler=None):
        handler = error_handler or (lambda msg: QMessageBox.warning(self, "Escalation failed", msg))
        self._set_busy(True)
        escalation_worker = EscalationWorker(job, self.provider, tier)
        escalation_worker.photo_updated.connect(self._on_escalation_done)
        escalation_worker.error.connect(handler)
        escalation_worker.start()
        escalation_worker.wait()
        # photo_updated/error are delivered as queued cross-thread signals (the
        # worker emits them from its own thread); pump the event loop once so
        # _on_escalation_done - and any automatic strong-tier follow-up it
        # triggers - runs before this call returns, same as every other
        # worker.wait()-then-processEvents() call site in this app.
        QApplication.instance().processEvents()
        self._set_busy(False)

    def _on_escalation_done(self, job):
        from cost import estimate_call_cost
        actual_cost = estimate_call_cost(self.provider, job.crop_decision.tier)
        job.last_cost = actual_cost
        self.gallery.update_job(job)
        self.decision_log.add(DecisionRecord(
            photo_name=job.filename, escalated=True, tier=job.crop_decision.tier,
            provider=self.provider.name, cost=actual_cost,
            confidence=job.crop_decision.confidence, timestamp=time.time(),
        ))
        self.gallery.refresh_cost()
        # Fully automatic tier escalation, no manual override (Global Constraints):
        # cheap tier first, escalate to strong only if confidence came back low.
        if job.crop_decision.tier == "cheap" and job.crop_decision.confidence < AUTO_ESCALATE_CONFIDENCE_THRESHOLD:
            self._run_escalation_worker(job, "strong")

    def _on_escalate_selected_clicked(self):
        selected = self.gallery.selected_for_escalation()
        if not selected:
            return
        if self.provider is None:
            self.statusBar().showMessage(
                "Escalation unavailable: no OpenAI API key configured (set OPENAI_API_KEY).", 5000)
            return
        confirm = EscalationConfirmDialog(self.provider, num_photos=len(selected), parent=self)
        confirm.exec()
        if not confirm.confirmed():
            return
        failed = []
        for job in selected:
            self._run_escalation_worker(
                job, "cheap", error_handler=lambda msg, j=job: failed.append(j.filename))
        succeeded = len(selected) - len(failed)
        if failed:
            summary = (
                f"Escalated {succeeded} of {len(selected)} — {len(failed)} failed: "
                f"{', '.join(failed)}.")
            self.statusBar().showMessage(summary, 8000)
            QMessageBox.warning(self, "Escalation finished with errors", summary)
        else:
            summary = f"Escalated {succeeded} of {len(selected)}."
            self.statusBar().showMessage(summary, 5000)
            QMessageBox.information(self, "Escalation complete", summary)

    def _on_manual_crop_requested(self, job):
        lay = H.layout(job.shape, job.canvas_long)
        dialog = CropEditorDialog(job, inner_ratio=lay["inner_ratio"], parent=self)
        dialog.exec()
        new_box = dialog.result_crop_box()
        if new_box is None:
            self.statusBar().showMessage("Manual crop cancelled.", 3000)
            return
        updated = P.apply_manual_crop(job, new_box)
        self.gallery.update_job(updated)
        self.statusBar().showMessage(f"Manual crop applied to {job.filename}.", 3000)

    def _on_details_requested(self, job):
        dialog = DetailViewDialog(job, decision_log=self.decision_log, parent=self)
        dialog.exec()

    def _on_clear_clicked(self):
        self.gallery.clear()
        self._update_save_button()
        self.statusBar().showMessage("Cleared.", 3000)

    def _on_save_clicked(self):
        kept = self.gallery.kept_jobs()
        out_folder = self.output_folder()
        self.settings.last_output_folder = out_folder
        self.settings.save(self.settings_path)
        written = save_kept_jobs(kept, out_folder)
        attempted = [j for j in kept if not j.error and j.rendered is not None]
        for j in attempted:
            if expected_output_path(j, out_folder) in written:
                self.gallery.remove_job(j.src_path)
        self._update_save_button()
        if len(written) < len(attempted):
            self.statusBar().showMessage(
                f"Saved {len(written)} of {len(attempted)} photo(s) — "
                f"{len(attempted) - len(written)} failed (check disk space/permissions).", 8000)
        else:
            self.statusBar().showMessage(f"Saved {len(written)} photo(s) to {out_folder}.", 5000)
