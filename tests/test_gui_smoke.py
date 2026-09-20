import os
import sys
import unittest
import unittest.mock

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

from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QSpinBox  # noqa: E402

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

    def test_run_settings_are_grouped_separately_from_folder_picker(self):
        panel = InputPanel(AppSettings())
        self.assertIn(panel.shape_combo, panel.settings_group.findChildren(QComboBox))
        self.assertIn(panel.canvas_spin, panel.settings_group.findChildren(QSpinBox))
        self.assertIn(panel.filter_checkbox, panel.settings_group.findChildren(QCheckBox))
        self.assertNotIn(panel.folder_edit, panel.settings_group.findChildren(QLineEdit))

    def test_process_folder_button_has_primary_weight_browse_does_not(self):
        panel = InputPanel(AppSettings())
        self.assertEqual(panel.process_button.property("primary"), True)
        self.assertNotEqual(panel.browse_button.property("primary"), True)


import tempfile
import time

import numpy as np
from PIL import Image

from gui.workers import EscalationWorker, ProcessFolderWorker  # noqa: E402
from providers.base import CropDecision  # noqa: E402
import hp5_emulate as H  # noqa: E402
import pipeline as P  # noqa: E402
import triage as tri  # noqa: E402


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

    def test_status_text_includes_cost_for_escalated_photo_with_known_cost(self):
        from providers.base import CropDecision
        job = _make_job()
        job.crop_decision = CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=0.82, tier="cheap")
        job.last_cost = 0.000123
        card = PhotoCard(job)
        self.assertIn("$0.000123", card.status_label.text())
        self.assertIn("cheap", card.status_label.text())
        self.assertIn("0.82", card.status_label.text())

    def test_status_text_omits_cost_when_unknown(self):
        from providers.base import CropDecision
        job = _make_job()
        job.crop_decision = CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=0.5, tier="strong")
        card = PhotoCard(job)
        self.assertNotIn("$", card.status_label.text())

    def _flagged_job(self, name="a.jpg"):
        import triage as tri
        job = _make_job(name)
        job.triage_decision = tri.TriageDecision(escalate=True, reasons=["test"])
        return job

    def test_escalate_checkbox_enabled_when_flagged_and_not_yet_decided(self):
        card = PhotoCard(self._flagged_job())
        self.assertTrue(card.escalate_checkbox.isEnabled())

    def test_escalate_checkbox_disabled_when_not_flagged(self):
        card = PhotoCard(_make_job())
        self.assertFalse(card.escalate_checkbox.isEnabled())

    def test_escalate_checkbox_disabled_once_crop_decision_is_set(self):
        from providers.base import CropDecision
        job = self._flagged_job()
        job.crop_decision = CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=0.9, tier="cheap")
        card = PhotoCard(job)
        self.assertFalse(card.escalate_checkbox.isEnabled())

    def test_escalate_checkbox_defaults_unchecked(self):
        card = PhotoCard(self._flagged_job())
        self.assertFalse(card.escalate_checkbox.isChecked())

    def test_update_job_disables_and_unchecks_escalate_checkbox_after_decision(self):
        from providers.base import CropDecision
        job = self._flagged_job()
        card = PhotoCard(job)
        card.escalate_checkbox.setChecked(True)
        job.crop_decision = CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=0.9, tier="cheap")
        card.update_job(job)
        self.assertFalse(card.escalate_checkbox.isEnabled())
        self.assertFalse(card.escalate_checkbox.isChecked())

    def test_escalate_selection_changed_signal_emitted_on_toggle(self):
        card = PhotoCard(self._flagged_job())
        received = []
        card.escalate_selection_changed.connect(lambda: received.append(True))
        card.escalate_checkbox.setChecked(True)
        self.assertEqual(received, [True])


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

    def test_remove_job_removes_only_that_card(self):
        gallery = ReviewGallery()
        job_a, job_b = _make_job("a.jpg"), _make_job("b.jpg")
        gallery.add_job(job_a)
        gallery.add_job(job_b)
        gallery.remove_job(job_a.src_path)
        self.assertEqual(list(gallery.cards.keys()), [job_b.src_path])
        self.assertEqual(gallery._grid.count(), 1)

    def test_remove_job_with_unknown_path_is_a_no_op(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        gallery.remove_job("/tmp/does-not-exist.jpg")
        self.assertEqual(len(gallery.cards), 1)

    def test_remove_job_reflows_remaining_cards_with_no_gaps(self):
        gallery = ReviewGallery()
        names = ["a.jpg", "b.jpg", "c.jpg", "d.jpg", "e.jpg"]
        jobs = [_make_job(n) for n in names]
        for job in jobs:
            gallery.add_job(job)
        # 5 cards at 4 columns: (0,0) (0,1) (0,2) (0,3) (1,0) - remove the
        # middle one and the rest must close the gap, not leave (0,2) empty.
        gallery.remove_job(jobs[2].src_path)

        remaining = [jobs[0], jobs[1], jobs[3], jobs[4]]
        expected_positions = [(0, 0), (0, 1), (0, 2), (0, 3)]
        for job, expected in zip(remaining, expected_positions):
            card = gallery.cards[job.src_path]
            index = gallery._grid.indexOf(card)
            row, col, _rowspan, _colspan = gallery._grid.getItemPosition(index)
            self.assertEqual((row, col), expected)

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

    def test_has_unsaved_kept_work_false_when_empty(self):
        gallery = ReviewGallery()
        self.assertFalse(gallery.has_unsaved_kept_work())

    def test_has_unsaved_kept_work_false_when_nothing_kept(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        self.assertFalse(gallery.has_unsaved_kept_work())

    def test_has_unsaved_kept_work_true_when_a_card_is_kept(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        gallery.cards["/tmp/a.jpg"].keep_checkbox.setChecked(True)
        self.assertTrue(gallery.has_unsaved_kept_work())

    def _flagged_job(self, name):
        import triage as tri
        job = _make_job(name)
        job.triage_decision = tri.TriageDecision(escalate=True, reasons=["test"])
        return job

    def test_selected_for_escalation_returns_only_checked_eligible_jobs(self):
        gallery = ReviewGallery()
        job_a, job_b = self._flagged_job("a.jpg"), self._flagged_job("b.jpg")
        gallery.add_job(job_a)
        gallery.add_job(job_b)
        gallery.cards["/tmp/a.jpg"].escalate_checkbox.setChecked(True)
        self.assertEqual(gallery.selected_for_escalation(), [job_a])

    def test_selected_for_escalation_empty_when_none_checked(self):
        gallery = ReviewGallery()
        gallery.add_job(self._flagged_job("a.jpg"))
        self.assertEqual(gallery.selected_for_escalation(), [])

    def test_empty_label_visible_when_no_jobs(self):
        gallery = ReviewGallery()
        self.assertFalse(gallery.empty_label.isHidden())

    def test_empty_label_hidden_after_add_job(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        self.assertTrue(gallery.empty_label.isHidden())

    def test_empty_label_reappears_after_clear(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        gallery.clear()
        self.assertFalse(gallery.empty_label.isHidden())

    def test_empty_label_reappears_after_removing_last_job(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        gallery.remove_job("/tmp/a.jpg")
        self.assertFalse(gallery.empty_label.isHidden())

    def test_cost_label_shows_running_total_from_decision_log(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(_Path(d) / "log.jsonl")
            log.add(DL.DecisionRecord(photo_name="a.jpg", escalated=True, tier="cheap",
                                       provider="openai", cost=0.001, confidence=0.9,
                                       timestamp=1.0))
            gallery = ReviewGallery(decision_log=log)
            gallery.refresh_cost()
            self.assertIn("0.001", gallery.cost_label.text())


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

    def test_shows_total_cost_from_decision_log_for_this_photo(self):
        import decision_log as DL
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(_Path(d) / "log.jsonl")
            log.add(DL.DecisionRecord(photo_name="a.jpg", escalated=True, tier="cheap",
                                       provider="openai", cost=0.0001, confidence=0.5,
                                       timestamp=1.0))
            log.add(DL.DecisionRecord(photo_name="a.jpg", escalated=True, tier="strong",
                                       provider="openai", cost=0.05, confidence=0.9,
                                       timestamp=2.0))
            log.add(DL.DecisionRecord(photo_name="other.jpg", escalated=True, tier="cheap",
                                       provider="openai", cost=1.0, confidence=0.5,
                                       timestamp=3.0))
            job = _make_job("a.jpg")
            dialog = DetailViewDialog(job, decision_log=log)
            self.assertIn("0.0501", dialog.info_label.text())


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

    def test_tall_photo_is_scaled_to_fit_the_available_screen_height(self):
        # A 1200px-tall canvas (the old hardcoded cap) plus the button box and
        # window chrome does not fit on a 900px-tall screen - the dialog must
        # scale further down so its own OK/Cancel buttons stay reachable.
        from PySide6.QtCore import QRect
        from PySide6.QtWidgets import QApplication as _QApp
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            Image.new("RGB", (1000, 3000), (100, 150, 200)).save(src)
            job = P.PhotoJob(src_path=src, filename="a.jpg", shape="portrait",
                              canvas_long=600, apply_filter=True)

            with unittest.mock.patch.object(
                    _QApp.primaryScreen(), "availableGeometry",
                    return_value=QRect(0, 0, 1200, 900)):
                dialog = CropEditorDialog(job, inner_ratio=0.5)

            # leave headroom for the button box + title bar/margins
            self.assertLessEqual(dialog._canvas.pixmap.height(), 900 - 100)


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


from gui.api_key_dialog import ApiKeyDialog  # noqa: E402


class ApiKeyDialogTests(unittest.TestCase):
    def test_prefills_field_with_currently_stored_key(self):
        with unittest.mock.patch("gui.api_key_dialog.store.get_stored_key", return_value="sk-existing"):
            dialog = ApiKeyDialog()
        self.assertEqual(dialog.key_edit.text(), "sk-existing")

    def test_field_is_masked(self):
        from PySide6.QtWidgets import QLineEdit
        with unittest.mock.patch("gui.api_key_dialog.store.get_stored_key", return_value=None):
            dialog = ApiKeyDialog()
        self.assertEqual(dialog.key_edit.echoMode(), QLineEdit.EchoMode.Password)

    def test_key_changed_false_before_any_action(self):
        with unittest.mock.patch("gui.api_key_dialog.store.get_stored_key", return_value=None):
            dialog = ApiKeyDialog()
        self.assertFalse(dialog.key_changed())

    def test_save_stores_key_and_marks_changed(self):
        with unittest.mock.patch("gui.api_key_dialog.store.get_stored_key", return_value=None), \
                unittest.mock.patch("gui.api_key_dialog.store.set_stored_key") as mock_set:
            dialog = ApiKeyDialog()
            dialog.key_edit.setText("sk-new-key")
            dialog._on_save_clicked()
            mock_set.assert_called_once_with("sk-new-key")
        self.assertTrue(dialog.key_changed())

    def test_save_with_blank_field_does_not_call_set_stored_key(self):
        with unittest.mock.patch("gui.api_key_dialog.store.get_stored_key", return_value=None), \
                unittest.mock.patch("gui.api_key_dialog.store.set_stored_key") as mock_set:
            dialog = ApiKeyDialog()
            dialog._on_save_clicked()
            mock_set.assert_not_called()

    def test_clear_calls_clear_stored_key_and_marks_changed(self):
        with unittest.mock.patch("gui.api_key_dialog.store.get_stored_key", return_value="sk-existing"), \
                unittest.mock.patch("gui.api_key_dialog.store.clear_stored_key") as mock_clear:
            dialog = ApiKeyDialog()
            dialog._on_clear_clicked()
            mock_clear.assert_called_once()
        self.assertTrue(dialog.key_changed())
        self.assertEqual(dialog.key_edit.text(), "")


import tempfile
from pathlib import Path as _Path

import decision_log as DL  # noqa: E402


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
        import api_key_store as aks
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            # Must not depend on whatever real key (if any) is saved in this
            # machine's actual OS keyring from manually testing "Configure API
            # key..." in the running app - that's real user data, not test
            # fixture state.
            with unittest.mock.patch.object(aks.keyring, "get_password", return_value=None), \
                    tempfile.TemporaryDirectory() as d:
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

    def test_starting_a_new_run_clears_the_previous_gallery(self):
        with tempfile.TemporaryDirectory() as config_dir, \
                tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            _write_synthetic(os.path.join(d1, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d2, "b.jpg"), seed=2)
            window = _make_window(config_dir)
            window._start_processing(d1, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 1)

            window._start_processing(d2, "square", 600, True)
            # clear() runs synchronously, before the new worker thread starts
            self.assertEqual(len(window.gallery.cards), 0)
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 1)
            self.assertIn("b.jpg", list(window.gallery.cards.values())[0].job.filename)

    def test_save_removes_saved_jobs_but_keeps_unselected_ones_visible(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d, "b.jpg"), seed=2)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 2)

            cards = list(window.gallery.cards.values())
            kept_card, other_card = cards[0], cards[1]
            kept_card.keep_checkbox.setChecked(True)
            window._on_save_clicked()

            self.assertNotIn(kept_card.job.src_path, window.gallery.cards)
            self.assertIn(other_card.job.src_path, window.gallery.cards)

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

    def test_has_a_sensible_minimum_window_size(self):
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)
            self.assertGreaterEqual(window.minimumWidth(), 800)
            self.assertGreaterEqual(window.minimumHeight(), 500)

    def test_configure_api_key_button_present(self):
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)
            self.assertIsNotNone(window.configure_api_key_button)

    def test_configure_api_key_reloads_provider_when_key_changed(self):
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)
            window.provider = None

            import gui.main_window as MW

            class FakeDialog:
                def __init__(self, parent=None):
                    pass

                def exec(self):
                    pass

                def key_changed(self):
                    return True

            fake_provider = object()
            with unittest.mock.patch.object(MW, "ApiKeyDialog", FakeDialog), \
                    unittest.mock.patch.object(MW, "OpenAICropProvider", return_value=fake_provider):
                window._on_configure_api_key_clicked()

            self.assertIs(window.provider, fake_provider)

    def test_configure_api_key_does_not_reload_provider_when_unchanged(self):
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)
            sentinel = object()
            window.provider = sentinel

            import gui.main_window as MW

            class FakeDialog:
                def __init__(self, parent=None):
                    pass

                def exec(self):
                    pass

                def key_changed(self):
                    return False

            with unittest.mock.patch.object(MW, "ApiKeyDialog", FakeDialog):
                window._on_configure_api_key_clicked()

            self.assertIs(window.provider, sentinel)

    def test_no_cost_panel_widget_remains(self):
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)
            self.assertFalse(hasattr(window, "cost_panel"))

    def test_gallery_cost_label_updates_after_escalation(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            job = list(window.gallery.cards.values())[0].job

            class FakeProvider:
                name = "openai"

                def price_per_million_tokens(self, tier):
                    return (1.0, 1.0)

                def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
                    return CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=0.9, tier=tier)

            window.provider = FakeProvider()
            window._run_escalation_worker(job, "cheap")

            self.assertNotIn("$0.000000", window.gallery.cost_label.text())

    def test_start_processing_asks_confirmation_when_gallery_has_unsaved_kept_work(self):
        with tempfile.TemporaryDirectory() as config_dir, \
                tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            _write_synthetic(os.path.join(d1, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d2, "b.jpg"), seed=2)
            window = _make_window(config_dir)
            window._start_processing(d1, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)

            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(QMessageBox, "question",
                                             return_value=QMessageBox.StandardButton.No) as mock_q:
                window._start_processing(d2, "square", 600, True)
                mock_q.assert_called_once()

            # user said No: the run must not have started, previous gallery untouched
            self.assertEqual(len(window.gallery.cards), 1)
            self.assertIn("a.jpg", list(window.gallery.cards.values())[0].job.filename)

    def test_start_processing_proceeds_when_confirmed(self):
        with tempfile.TemporaryDirectory() as config_dir, \
                tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            _write_synthetic(os.path.join(d1, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d2, "b.jpg"), seed=2)
            window = _make_window(config_dir)
            window._start_processing(d1, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)

            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(QMessageBox, "question",
                                             return_value=QMessageBox.StandardButton.Yes):
                window._start_processing(d2, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()

            self.assertEqual(len(window.gallery.cards), 1)
            self.assertIn("b.jpg", list(window.gallery.cards.values())[0].job.filename)

    def test_start_processing_does_not_ask_when_nothing_kept(self):
        with tempfile.TemporaryDirectory() as config_dir, \
                tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            _write_synthetic(os.path.join(d1, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d2, "b.jpg"), seed=2)
            window = _make_window(config_dir)
            window._start_processing(d1, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()

            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(QMessageBox, "question") as mock_q:
                window._start_processing(d2, "square", 600, True)
                mock_q.assert_not_called()

    def test_busy_indicator_hidden_initially(self):
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)
            self.assertTrue(window.busy_indicator.isHidden())

    def test_start_processing_shows_busy_indicator_until_finished(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            self.assertFalse(window.busy_indicator.isHidden())
            window._worker.wait(10000)
            _app.processEvents()
            self.assertTrue(window.busy_indicator.isHidden())

    def test_save_button_disabled_when_nothing_kept(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            self.assertFalse(window.save_button.isEnabled())

    def test_save_button_enables_and_disables_with_keep_checkbox(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            card = list(window.gallery.cards.values())[0]

            card.keep_checkbox.setChecked(True)
            self.assertTrue(window.save_button.isEnabled())

            card.keep_checkbox.setChecked(False)
            self.assertFalse(window.save_button.isEnabled())

    def test_save_button_disabled_after_clear(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)
            self.assertTrue(window.save_button.isEnabled())

            window._on_clear_clicked()

            self.assertFalse(window.save_button.isEnabled())

    def test_save_button_disabled_after_saving_all_kept(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)

            window._on_save_clicked()

            self.assertFalse(window.save_button.isEnabled())

    def test_escalate_selected_button_disabled_with_no_selection(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            self.assertFalse(window.escalate_selected_button.isEnabled())

    def test_escalate_selected_button_enables_when_a_card_is_selected(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            job = list(window.gallery.cards.values())[0].job
            job.triage_decision = tri.TriageDecision(escalate=True, reasons=["test"])
            card = list(window.gallery.cards.values())[0]
            card.update_job(job)

            card.escalate_checkbox.setChecked(True)
            self.assertTrue(window.escalate_selected_button.isEnabled())

            card.escalate_checkbox.setChecked(False)
            self.assertFalse(window.escalate_selected_button.isEnabled())

    def test_escalate_selected_processes_all_selected_photos_and_reports_summary(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d, "b.jpg"), seed=2)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()

            cards = list(window.gallery.cards.values())
            for card in cards:
                job = card.job
                job.triage_decision = tri.TriageDecision(escalate=True, reasons=["test"])
                card.update_job(job)
                card.escalate_checkbox.setChecked(True)

            calls = []

            class FakeProvider:
                name = "openai"

                def price_per_million_tokens(self, tier):
                    return (1.0, 1.0)

                def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
                    calls.append(tier)
                    return CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=0.9, tier=tier)

            window.provider = FakeProvider()

            import gui.main_window as MW
            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(MW.EscalationConfirmDialog, "exec", return_value=None), \
                    unittest.mock.patch.object(MW.EscalationConfirmDialog, "confirmed", return_value=True), \
                    unittest.mock.patch.object(QMessageBox, "information") as mock_info:
                window._on_escalate_selected_clicked()

            self.assertEqual(len(calls), 2)
            self.assertIn("Escalated 2 of 2", window.statusBar().currentMessage())
            mock_info.assert_called_once()
            self.assertIn("Escalated 2 of 2", mock_info.call_args.args[2])

    def test_escalate_selected_reports_partial_failure(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d, "b.jpg"), seed=2)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()

            cards = list(window.gallery.cards.values())
            for card in cards:
                job = card.job
                job.triage_decision = tri.TriageDecision(escalate=True, reasons=["test"])
                card.update_job(job)
                card.escalate_checkbox.setChecked(True)

            failing_filename = cards[0].job.filename

            class FakeProvider:
                name = "openai"

                def price_per_million_tokens(self, tier):
                    return (1.0, 1.0)

                def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
                    return CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=0.9, tier=tier)

            window.provider = FakeProvider()

            import pipeline as P_

            original_apply_escalation = P_.apply_escalation

            def patched_apply_escalation(job, provider, tier):
                if job.filename == failing_filename:
                    raise RuntimeError("boom")
                return original_apply_escalation(job, provider, tier)

            import gui.main_window as MW
            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(MW.EscalationConfirmDialog, "exec", return_value=None), \
                    unittest.mock.patch.object(MW.EscalationConfirmDialog, "confirmed", return_value=True), \
                    unittest.mock.patch.object(P_, "apply_escalation", side_effect=patched_apply_escalation), \
                    unittest.mock.patch.object(QMessageBox, "warning") as mock_warn:
                window._on_escalate_selected_clicked()

            msg = window.statusBar().currentMessage()
            self.assertIn("Escalated 1 of 2", msg)
            self.assertIn(failing_filename, msg)
            mock_warn.assert_called_once()
            self.assertIn(failing_filename, mock_warn.call_args.args[2])

    def test_escalation_worker_hides_busy_indicator_when_done(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            job = list(window.gallery.cards.values())[0].job

            class FakeProvider:
                name = "openai"

                def price_per_million_tokens(self, tier):
                    return (1.0, 1.0)

                def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
                    return CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=0.9, tier=tier)

            window.provider = FakeProvider()
            window._run_escalation_worker(job, "cheap")
            self.assertTrue(window.busy_indicator.isHidden())


if __name__ == "__main__":
    unittest.main()
