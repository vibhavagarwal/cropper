import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])


class MainWindowSmokeTests(unittest.TestCase):
    def test_main_window_constructs(self):
        from gui.main_window import MainWindow
        window = MainWindow()
        self.assertIsNotNone(window.settings)


from PySide6.QtCore import QMimeData, QUrl, Qt, QTimer
from PySide6.QtGui import QDropEvent
from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialogButtonBox

from gui.input_panel import InputPanel  # noqa: E402
from settings import AppSettings  # noqa: E402


class InputPanelTests(unittest.TestCase):
    def test_defaults_come_from_settings(self):
        panel = InputPanel(AppSettings(shape="portrait", canvas_long=1800, apply_filter=False))
        self.assertEqual(panel.shape_combo.currentText(), "portrait")
        self.assertEqual(panel.canvas_spin.value(), 1800)
        self.assertFalse(panel.filter_checkbox.isChecked())

    def test_process_requested_emits_current_values(self):
        panel = InputPanel(AppSettings())
        panel.folder_edit.setText("C:/photos")
        panel.shape_combo.setCurrentText("landscape")
        panel.canvas_spin.setValue(3000)
        panel.filter_checkbox.setChecked(False)

        received = []
        panel.process_requested.connect(lambda *args: received.append(args))
        panel._on_process_clicked()

        self.assertEqual(received, [("C:/photos", "landscape", 3000, False)])

    def test_current_folder_reflects_folder_edit(self):
        panel = InputPanel(AppSettings())
        panel.folder_edit.setText("C:/some/folder")
        self.assertEqual(panel.current_folder(), "C:/some/folder")


import tempfile
import time

import numpy as np
from PIL import Image

from gui.workers import EscalationWorker, ProcessFolderWorker  # noqa: E402
from providers.base import CropDecision  # noqa: E402
import hp5_emulate as H  # noqa: E402
import pipeline as P  # noqa: E402


def _write_synthetic(path, seed=0):
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(200, 300, 3), dtype=np.uint8)
    Image.fromarray(arr).save(path, quality=95)


class ProcessFolderWorkerTests(unittest.TestCase):
    def test_worker_emits_one_signal_per_photo_then_finishes(self):
        with tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d, "b.jpg"), seed=2)

            received = []
            worker = ProcessFolderWorker(d, "square", 600, True)
            worker.photo_ready.connect(lambda job: received.append(job))
            done = []
            worker.finished_all.connect(lambda: done.append(True))
            worker.start()
            worker.wait(10000)
            _app.processEvents()

            self.assertEqual(len(received), 2)
            self.assertEqual(done, [True])


class EscalationWorkerTests(unittest.TestCase):
    def test_worker_emits_updated_job_on_success(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            _write_synthetic(src)
            job = P.process_photo(src, "square", 600, True)

            class FakeProvider:
                def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
                    return CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=0.9, tier=tier)

            received = []
            worker = EscalationWorker(job, FakeProvider(), "strong")
            worker.photo_updated.connect(lambda j: received.append(j))
            worker.start()
            worker.wait(10000)
            _app.processEvents()

            self.assertEqual(len(received), 1)
            self.assertEqual(received[0].crop_decision.tier, "strong")

    def test_worker_emits_error_signal_on_failure(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            _write_synthetic(src)
            job = P.process_photo(src, "square", 600, True)

            class FailingProvider:
                def request_crop(self, *a, **kw):
                    raise RuntimeError("api down")

            errors = []
            worker = EscalationWorker(job, FailingProvider(), "cheap")
            worker.error.connect(lambda msg: errors.append(msg))
            worker.start()
            worker.wait(10000)
            _app.processEvents()

            self.assertEqual(errors, ["api down"])


from gui.review_gallery import PhotoCard, ReviewGallery  # noqa: E402


def _make_job(name="a.jpg", keep=False):
    job = P.PhotoJob(src_path=f"/tmp/{name}", filename=name, shape="square",
                      canvas_long=600, apply_filter=True)
    job.rendered = Image.new("L", (600, 600), 128)
    job.keep = keep
    return job


class PhotoCardTests(unittest.TestCase):
    def test_card_holds_job_and_keep_checkbox_defaults_unchecked(self):
        card = PhotoCard(_make_job())
        self.assertFalse(card.keep_checkbox.isChecked())

    def test_toggling_checkbox_updates_job_keep_flag(self):
        card = PhotoCard(_make_job())
        card.keep_checkbox.setChecked(True)
        self.assertTrue(card.job.keep)

    def test_escalate_button_emits_signal_with_job(self):
        job = _make_job()
        card = PhotoCard(job)
        received = []
        card.escalate_requested.connect(lambda j: received.append(j))
        card._on_escalate_clicked()
        self.assertEqual(received, [job])


class ReviewGalleryTests(unittest.TestCase):
    def test_add_job_creates_a_card(self):
        gallery = ReviewGallery()
        job = _make_job("a.jpg")
        gallery.add_job(job)
        self.assertIn(job.src_path, gallery.cards)

    def test_kept_jobs_returns_only_checked_ones(self):
        gallery = ReviewGallery()
        job_a, job_b = _make_job("a.jpg"), _make_job("b.jpg")
        gallery.add_job(job_a)
        gallery.add_job(job_b)
        gallery.cards[job_a.src_path].keep_checkbox.setChecked(True)
        kept = gallery.kept_jobs()
        self.assertEqual(kept, [job_a])

    def test_update_job_refreshes_existing_card(self):
        gallery = ReviewGallery()
        job = _make_job("a.jpg")
        gallery.add_job(job)
        job.rendered = Image.new("L", (600, 600), 200)
        gallery.update_job(job)
        self.assertIs(gallery.cards[job.src_path].job, job)

    def test_clear_removes_all_cards(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        gallery.add_job(_make_job("b.jpg"))
        gallery.clear()
        self.assertEqual(gallery.cards, {})
        self.assertEqual(gallery._grid.count(), 0)

    def test_clear_then_add_job_starts_grid_layout_over(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        gallery.clear()
        gallery.add_job(_make_job("b.jpg"))
        self.assertEqual(list(gallery.cards.keys()), ["/tmp/b.jpg"])


from gui.detail_view_dialog import DetailViewDialog, render_detection_overlay  # noqa: E402
from detection import DetectionResult, FaceBox, SaliencyResult  # noqa: E402


class DetectionOverlayTests(unittest.TestCase):
    def test_overlay_is_same_size_as_source_and_marks_a_face(self):
        job = _make_job("a.jpg")
        job.detection = DetectionResult(
            faces=[FaceBox(10, 10, 40, 40)],
            saliency=SaliencyResult(heatmap=np.zeros((600, 600), dtype="float32"),
                                     blob_fraction=0.2, touches_edge=False),
            symmetry_score=0.9,
        )
        overlay = render_detection_overlay(job)
        self.assertEqual(overlay.size, job.rendered.size)
        # Face (10,10,40,40) in a 600x600 source maps through layout("square", 600)
        # (border=12px, inner=576px) to a drawn box at roughly x:[21,60], y:[21,60]
        # on the rendered canvas - not (10,10)-(50,50), because the overlay now
        # correctly accounts for the border offset and inner-canvas scaling.
        overlay_arr = np.asarray(overlay.convert("RGB"))
        self.assertFalse((overlay_arr[30, 15:65] == overlay_arr[30, 15, 0]).all())


class DetailViewDialogTests(unittest.TestCase):
    def test_dialog_constructs_with_job(self):
        job = _make_job("a.jpg")
        job.detection = DetectionResult(
            faces=[], saliency=SaliencyResult(heatmap=np.zeros((10, 10), dtype="float32"),
                                               blob_fraction=0.0, touches_edge=False),
            symmetry_score=0.5,
        )
        dialog = DetailViewDialog(job)
        self.assertIsNotNone(dialog)


from gui.crop_editor_dialog import CropEditorDialog  # noqa: E402


class CropEditorDialogTests(unittest.TestCase):
    def test_dialog_constructs_and_starts_with_no_result(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            Image.new("RGB", (800, 600), (128, 128, 128)).save(src)
            job = P.PhotoJob(src_path=src, filename="a.jpg", shape="square",
                              canvas_long=600, apply_filter=True)
            job.rendered = Image.new("L", (600, 600), 128)
            dialog = CropEditorDialog(job, inner_ratio=1.0)
            self.assertIsNone(dialog.result_crop_box())

    def test_manual_crop_uses_correct_ratio_for_non_square_source(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            # 4000x3000 source, square (1:1) target shape -> true inner_ratio is 1.0,
            # NOT 0.75 (which is what a buggy fraction-based computation would give)
            Image.new("RGB", (4000, 3000), (100, 150, 200)).save(src)
            job = P.process_photo(src, shape="square", canvas_long=600, apply_filter=False)
            self.assertIsNone(job.error)
            lay_ratio = H.layout(job.shape, job.canvas_long)["inner_ratio"]
            self.assertAlmostEqual(lay_ratio, 1.0, places=3)
            dialog = CropEditorDialog(job, inner_ratio=lay_ratio)
            self.assertAlmostEqual(dialog.state.ratio, 1.0, places=3)
            # the dialog's displayed image must preserve the source's aspect ratio
            # (4000x3000 = 4:3), not be squashed to some other shape
            self.assertAlmostEqual(dialog._canvas.pixmap.width() / dialog._canvas.pixmap.height(),
                                    4000 / 3000, places=2)


from gui.escalation_dialog import EscalationConfirmDialog  # noqa: E402


class EscalationConfirmDialogTests(unittest.TestCase):
    def test_shows_worst_case_cost_and_defaults_unconfirmed(self):
        class FakeProvider:
            def price_per_million_tokens(self, tier):
                return (10.0, 50.0)

        dialog = EscalationConfirmDialog(FakeProvider(), num_photos=3)
        self.assertFalse(dialog.confirmed())
        self.assertIn("$", dialog.cost_label.text())

    def test_accept_marks_confirmed(self):
        class FakeProvider:
            def price_per_million_tokens(self, tier):
                return (10.0, 50.0)

        dialog = EscalationConfirmDialog(FakeProvider(), num_photos=1)
        dialog._on_accept()
        self.assertTrue(dialog.confirmed())


import tempfile
from pathlib import Path as _Path

from gui.cost_panel import CostPanel  # noqa: E402
import decision_log as DL  # noqa: E402


class CostPanelTests(unittest.TestCase):
    def test_refresh_shows_running_total_and_history_rows(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(_Path(d) / "log.jsonl")
            log.add(DL.DecisionRecord(photo_name="a.jpg", escalated=True, tier="cheap",
                                       provider="openai", cost=0.001, confidence=0.9,
                                       timestamp=1.0))
            panel = CostPanel(log)
            panel.refresh()
            self.assertIn("0.001", panel.total_label.text())
            self.assertEqual(panel.history_list.count(), 1)

    def test_refresh_after_new_record_updates_total(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(_Path(d) / "log.jsonl")
            panel = CostPanel(log)
            panel.refresh()
            log.add(DL.DecisionRecord(photo_name="b.jpg", escalated=True, tier="strong",
                                       provider="openai", cost=0.05, confidence=0.3,
                                       timestamp=2.0))
            panel.refresh()
            self.assertIn("0.05", panel.total_label.text())
            self.assertEqual(panel.history_list.count(), 1)


from gui.save_action import save_kept_jobs  # noqa: E402


class SaveActionTests(unittest.TestCase):
    def test_saves_only_kept_jobs_to_output_folder(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = os.path.join(d, "out")
            job_a = _make_job("a.jpg", keep=True)
            job_b = _make_job("b.jpg", keep=False)
            written = save_kept_jobs([job_a, job_b], out_dir)
            self.assertEqual(len(written), 1)
            self.assertTrue(os.path.exists(written[0]))
            self.assertIn("a", os.path.basename(written[0]))

    def test_skips_jobs_with_errors_even_if_marked_keep(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = os.path.join(d, "out")
            job = _make_job("a.jpg", keep=True)
            job.error = "boom"
            written = save_kept_jobs([job], out_dir)
            self.assertEqual(written, [])

    def test_creates_output_folder_if_missing(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = os.path.join(d, "does", "not", "exist", "yet")
            job = _make_job("a.jpg", keep=True)
            save_kept_jobs([job], out_dir)
            self.assertTrue(os.path.isdir(out_dir))


def _make_window(config_dir):
    """Build a MainWindow rooted at a throwaway config dir instead of the
    developer's real ~/.cropper, so tests never touch a real home directory."""
    from gui.main_window import MainWindow
    return MainWindow(
        settings_path=_Path(config_dir) / "settings.json",
        decision_log_path=_Path(config_dir) / "decision_log.jsonl",
    )


class MainWindowWiringTests(unittest.TestCase):
    def test_main_window_constructs_without_openai_api_key(self):
        from gui.main_window import MainWindow
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with tempfile.TemporaryDirectory() as d:
                window = MainWindow(settings_path=_Path(d) / "settings.json",
                                     decision_log_path=_Path(d) / "decision_log.jsonl")
                self.assertIsNone(window.provider)
        finally:
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key

    def test_default_output_folder_is_input_folder_slash_out(self):
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)
            window.input_panel.folder_edit.setText("/tmp/photos")
            self.assertEqual(window.output_folder(), "/tmp/photos/out")

    def test_processing_a_folder_populates_the_gallery(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window.input_panel.folder_edit.setText(d)
            window.input_panel.shape_combo.setCurrentText("square")
            window.input_panel.canvas_spin.setValue(600)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 1)

    def test_save_writes_only_kept_jobs(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)
            window._on_save_clicked()
            out_dir = os.path.join(d, "out")
            self.assertTrue(os.path.isdir(out_dir))
            self.assertEqual(len(os.listdir(out_dir)), 1)

    def test_low_confidence_cheap_tier_automatically_escalates_to_strong(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            job = list(window.gallery.cards.values())[0].job

            calls = []

            class FakeProvider:
                name = "openai"

                def price_per_million_tokens(self, tier):
                    return (1.0, 1.0)

                def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
                    calls.append(tier)
                    confidence = 0.3 if tier == "cheap" else 0.95
                    return CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=confidence, tier=tier)

            window.provider = FakeProvider()
            window._run_escalation_worker(job, "cheap")
            self.assertEqual(calls, ["cheap", "strong"])

    def test_clear_button_empties_the_gallery(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 1)

            QTest.mouseClick(window.clear_button, Qt.LeftButton)

            self.assertEqual(len(window.gallery.cards), 0)

    def test_manual_crop_accept_shows_status_message_and_updates_rendered(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            job = list(window.gallery.cards.values())[0].job
            rendered_before = job.rendered

            def accept_dialog():
                dlg = _app.activeModalWidget()
                dlg.findChild(QDialogButtonBox).button(
                    QDialogButtonBox.StandardButton.Ok).click()

            QTimer.singleShot(0, accept_dialog)
            window._on_manual_crop_requested(job)

            self.assertIn("Manual crop applied", window.statusBar().currentMessage())
            self.assertIsNot(job.rendered, rendered_before)

    def test_manual_crop_cancel_shows_status_message_and_leaves_job_unchanged(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            job = list(window.gallery.cards.values())[0].job
            rendered_before = job.rendered

            def cancel_dialog():
                dlg = _app.activeModalWidget()
                dlg.findChild(QDialogButtonBox).button(
                    QDialogButtonBox.StandardButton.Cancel).click()

            QTimer.singleShot(0, cancel_dialog)
            window._on_manual_crop_requested(job)

            self.assertIn("cancelled", window.statusBar().currentMessage())
            self.assertIs(job.rendered, rendered_before)


if __name__ == "__main__":
    unittest.main()
