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


from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtCore import QPoint

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
        # a pixel on the drawn face-box border should differ from plain mid-gray background
        overlay_arr = np.asarray(overlay.convert("RGB"))
        self.assertFalse((overlay_arr[10, 10:50] == overlay_arr[10, 10, 0]).all())


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
        job = _make_job("a.jpg")
        dialog = CropEditorDialog(job, inner_ratio=1.0)
        self.assertIsNone(dialog.result_crop_box())


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


if __name__ == "__main__":
    unittest.main()
