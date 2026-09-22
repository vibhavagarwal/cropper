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

from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QLineEdit, QSpinBox  # noqa: E402

from gui.input_panel import InputPanel  # noqa: E402
from settings import AppSettings  # noqa: E402


class InputPanelTests(unittest.TestCase):
    def test_defaults_come_from_settings(self):
        panel = InputPanel(AppSettings(shape="portrait", canvas_long=1800, apply_bw=False,
                                        apply_grain=False, grain_size="large",
                                        border_size="large"))
        self.assertEqual(panel.shape_combo.currentText(), "portrait")
        self.assertEqual(panel.canvas_spin.value(), 1800)
        self.assertFalse(panel.bw_checkbox.isChecked())
        self.assertFalse(panel.grain_checkbox.isChecked())
        self.assertEqual(panel.grain_size_combo.currentText(), "large")
        self.assertEqual(panel.border_size_combo.currentText(), "large")

    def test_process_requested_emits_current_values(self):
        panel = InputPanel(AppSettings())
        panel.folder_edit.setText("C:/photos")
        panel.shape_combo.setCurrentText("landscape")
        panel.canvas_spin.setValue(3000)
        panel.bw_checkbox.setChecked(False)
        panel.grain_checkbox.setChecked(False)
        panel.grain_size_combo.setCurrentText("small")
        panel.border_size_combo.setCurrentText("medium")

        received = []
        panel.process_requested.connect(lambda *args: received.append(args))
        panel._on_process_button_clicked()

        self.assertEqual(received, [("C:/photos", "landscape", 3000, False, False, "small",
                                      "medium")])

    def test_current_folder_reflects_folder_edit(self):
        panel = InputPanel(AppSettings())
        panel.folder_edit.setText("C:/some/folder")
        self.assertEqual(panel.current_folder(), "C:/some/folder")

    def test_run_settings_are_grouped_separately_from_folder_picker(self):
        panel = InputPanel(AppSettings())
        self.assertIn(panel.shape_combo, panel.settings_group.findChildren(QComboBox))
        self.assertIn(panel.canvas_spin, panel.settings_group.findChildren(QSpinBox))
        self.assertIn(panel.bw_checkbox, panel.settings_group.findChildren(QCheckBox))
        self.assertIn(panel.grain_checkbox, panel.settings_group.findChildren(QCheckBox))
        self.assertIn(panel.grain_size_combo, panel.settings_group.findChildren(QComboBox))
        self.assertIn(panel.border_size_combo, panel.settings_group.findChildren(QComboBox))
        self.assertNotIn(panel.folder_edit, panel.settings_group.findChildren(QLineEdit))

    def test_process_button_sits_next_to_browse_in_the_folder_row(self):
        panel = InputPanel(AppSettings())
        panel.show()
        _app.processEvents()
        # Same row as Browse (not down in its own row below Run settings),
        # positioned after it.
        self.assertAlmostEqual(panel.process_button.y(), panel.browse_button.y(), delta=4)
        self.assertGreater(panel.process_button.x(), panel.browse_button.x())
        self.assertLess(panel.browse_button.y(), panel.settings_group.y())

    def test_process_folder_button_has_primary_weight_browse_does_not(self):
        panel = InputPanel(AppSettings())
        self.assertEqual(panel.process_button.property("primary"), True)
        self.assertNotEqual(panel.browse_button.property("primary"), True)

    def test_browsing_to_a_folder_emits_folder_selected(self):
        panel = InputPanel(AppSettings())
        received = []
        panel.folder_selected.connect(received.append)
        with unittest.mock.patch.object(
                QFileDialog, "getExistingDirectory", return_value="C:/photos"):
            panel._on_browse_clicked()
        self.assertEqual(received, ["C:/photos"])

    def test_cancelling_browse_does_not_emit_folder_selected(self):
        panel = InputPanel(AppSettings())
        received = []
        panel.folder_selected.connect(received.append)
        with unittest.mock.patch.object(QFileDialog, "getExistingDirectory", return_value=""):
            panel._on_browse_clicked()
        self.assertEqual(received, [])

    def test_typing_in_folder_edit_does_not_emit_folder_selected(self):
        panel = InputPanel(AppSettings())
        received = []
        panel.folder_selected.connect(received.append)
        panel.folder_edit.setText("C:/typed/path")
        self.assertEqual(received, [])

    def test_process_button_emits_process_requested_when_idle(self):
        panel = InputPanel(AppSettings())
        received = []
        panel.process_requested.connect(lambda *args: received.append(args))
        stop_received = []
        panel.stop_requested.connect(lambda: stop_received.append(True))
        panel._on_process_button_clicked()
        self.assertEqual(len(received), 1)
        self.assertEqual(stop_received, [])

    def test_process_button_emits_stop_requested_when_processing(self):
        panel = InputPanel(AppSettings())
        panel.set_processing(True)
        received = []
        panel.process_requested.connect(lambda *args: received.append(args))
        stop_received = []
        panel.stop_requested.connect(lambda: stop_received.append(True))
        panel._on_process_button_clicked()
        self.assertEqual(received, [])
        self.assertEqual(stop_received, [True])

    def test_set_processing_toggles_button_text(self):
        panel = InputPanel(AppSettings())
        self.assertEqual(panel.process_button.text(), "Process Folder")
        panel.set_processing(True)
        self.assertEqual(panel.process_button.text(), "Stop")
        panel.set_processing(False)
        self.assertEqual(panel.process_button.text(), "Process Folder")

    def test_dropping_a_folder_emits_folder_selected(self):
        panel = InputPanel(AppSettings())
        received = []
        panel.folder_selected.connect(received.append)

        class FakeMimeData:
            def hasUrls(self):
                return True

            def urls(self):
                return [QUrl.fromLocalFile("C:/dropped")]

        class FakeEvent:
            def mimeData(self):
                return FakeMimeData()

            def acceptProposedAction(self):
                pass

        with unittest.mock.patch("os.path.isdir", return_value=True):
            panel.dropEvent(FakeEvent())
        self.assertEqual(received, ["C:/dropped"])

    def test_settings_group_splits_into_two_rows_so_widgets_do_not_overlap(self):
        # Regression test: the settings row grew (grain size, then border
        # size) inside a single QHBoxLayout with no wrap - at narrow widths
        # the widgets got squeezed below their natural size and overlapped.
        # It's now two stacked rows within the group box.
        panel = InputPanel(AppSettings())
        panel.show()
        panel.resize(900, 200)
        _app.processEvents()
        widgets = [panel.shape_combo, panel.canvas_spin, panel.bw_checkbox,
                   panel.grain_checkbox, panel.grain_size_combo, panel.border_size_combo]
        for w in widgets:
            self.assertGreater(w.width(), 0)
        rects = [w.geometry() for w in widgets]
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                self.assertFalse(a.intersects(b), f"{widgets[i]} overlaps a sibling")


import tempfile
import time

import numpy as np
from PIL import Image

from gui.workers import EscalationWorker, FolderPreviewWorker, ProcessFolderWorker  # noqa: E402
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
            worker = ProcessFolderWorker(d, "square", 600, True, True, "medium", "small")
            worker.photo_ready.connect(lambda job: received.append(job))
            done = []
            worker.finished_all.connect(lambda: done.append(True))
            worker.start()
            worker.wait(10000)
            _app.processEvents()

            self.assertEqual(len(received), 2)
            self.assertEqual(done, [True])

    def test_stop_before_start_processes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d, "b.jpg"), seed=2)

            received = []
            worker = ProcessFolderWorker(d, "square", 600, True, True, "medium", "small")
            worker.photo_ready.connect(lambda job: received.append(job))
            done = []
            worker.finished_all.connect(lambda: done.append(True))
            worker.stop()
            worker.start()
            worker.wait(10000)
            _app.processEvents()

            self.assertEqual(received, [])
            self.assertEqual(done, [True])  # still exits run() cleanly

    def test_stop_mid_run_halts_before_remaining_photos(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(5):
                _write_synthetic(os.path.join(d, f"{i}.jpg"), seed=i)

            original = P.process_photo

            def slow(*a, **kw):
                time.sleep(0.05)
                return original(*a, **kw)

            received = []
            worker = ProcessFolderWorker(d, "square", 600, True, True, "medium", "small")
            worker.photo_ready.connect(lambda job: received.append(job))
            done = []
            worker.finished_all.connect(lambda: done.append(True))
            with unittest.mock.patch.object(P, "process_photo", side_effect=slow):
                worker.start()
                deadline = time.time() + 10
                while not received and time.time() < deadline:
                    _app.processEvents()
                    time.sleep(0.01)
                worker.stop()
                worker.wait(10000)
                _app.processEvents()

            self.assertTrue(done)
            self.assertGreaterEqual(len(received), 1)
            self.assertLess(len(received), 5)


class FolderPreviewWorkerTests(unittest.TestCase):
    def test_worker_emits_one_unprocessed_preview_per_photo_then_finishes(self):
        with tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d, "b.jpg"), seed=2)

            received = []
            worker = FolderPreviewWorker(d, "square", 600, True, True, "medium", "small")
            worker.preview_ready.connect(lambda job: received.append(job))
            done = []
            worker.finished_all.connect(lambda: done.append(True))
            worker.start()
            worker.wait(10000)
            _app.processEvents()

            self.assertEqual(len(received), 2)
            self.assertTrue(all(not job.processed for job in received))
            self.assertTrue(all(job.rendered is not None for job in received))
            self.assertEqual(done, [True])


class EscalationWorkerTests(unittest.TestCase):
    def test_worker_emits_updated_job_on_success(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            _write_synthetic(src)
            job = P.process_photo(src, "square", 600, True, True, "medium", "small")

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
            job = P.process_photo(src, "square", 600, True, True, "medium", "small")

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
                      canvas_long=600, apply_bw=True, apply_grain=True, grain_size="medium",
                      border_size="small")
    job.rendered = Image.new("L", (600, 600), 128)
    job.keep = keep
    return job


def _make_preview_job(name="a.jpg"):
    job = P.PhotoJob(src_path=f"/tmp/{name}", filename=name, shape="square",
                      canvas_long=600, apply_bw=True, apply_grain=True, grain_size="medium",
                      border_size="small", processed=False)
    job.rendered = Image.new("RGB", (600, 600), (128, 128, 128))
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

    def test_preview_card_shows_not_yet_processed_and_disables_controls(self):
        card = PhotoCard(_make_preview_job())
        self.assertEqual(card.status_label.text(), "not yet processed")
        self.assertFalse(card.keep_checkbox.isEnabled())
        self.assertFalse(card.crop_button.isEnabled())
        self.assertFalse(card.details_button.isEnabled())
        self.assertFalse(card.escalate_checkbox.isEnabled())

    def test_update_job_upgrades_preview_card_to_processed_state(self):
        card = PhotoCard(_make_preview_job())
        processed = _make_job()
        card.update_job(processed)
        self.assertEqual(card.status_label.text(), "formula crop")
        self.assertTrue(card.keep_checkbox.isEnabled())
        self.assertTrue(card.crop_button.isEnabled())
        self.assertTrue(card.details_button.isEnabled())

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
        gallery.resize(1100, 600)  # wide enough for 4 columns at 248px cards
        _app.processEvents()
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

    def test_column_count_derived_from_available_width(self):
        gallery = ReviewGallery()
        gallery.resize(600, 400)  # room for ~2 columns at 248px + spacing
        _app.processEvents()
        jobs = [_make_job(f"{i}.jpg") for i in range(4)]
        for job in jobs:
            gallery.add_job(job)
        expected_cols = gallery._column_count()
        self.assertGreaterEqual(expected_cols, 1)
        for i, job in enumerate(jobs):
            card = gallery.cards[job.src_path]
            index = gallery._grid.indexOf(card)
            row, col, _rowspan, _colspan = gallery._grid.getItemPosition(index)
            self.assertEqual((row, col), divmod(i, expected_cols))

    def test_gallery_reflows_existing_cards_on_resize_to_wider_width(self):
        gallery = ReviewGallery()
        gallery.show()  # resizeEvent only fires for a widget that's been shown
        gallery.resize(400, 400)  # narrow: forces 1 column
        _app.processEvents()
        jobs = [_make_job(f"{i}.jpg") for i in range(3)]
        for job in jobs:
            gallery.add_job(job)
        narrow_cols = gallery._column_count()
        self.assertEqual(narrow_cols, 1)
        for i, job in enumerate(jobs):
            card = gallery.cards[job.src_path]
            index = gallery._grid.indexOf(card)
            row, col, _rowspan, _colspan = gallery._grid.getItemPosition(index)
            self.assertEqual((row, col), (i, 0))

        gallery.resize(1100, 400)  # wide enough for multiple columns
        _app.processEvents()
        wide_cols = gallery._column_count()
        self.assertGreater(wide_cols, narrow_cols)
        for i, job in enumerate(jobs):
            card = gallery.cards[job.src_path]
            index = gallery._grid.indexOf(card)
            row, col, _rowspan, _colspan = gallery._grid.getItemPosition(index)
            self.assertEqual((row, col), divmod(i, wide_cols))

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
        self.assertFalse(gallery._empty_wrapper.isHidden())

    def test_empty_label_stays_compact_in_a_tall_gallery(self):
        # Regression test: with no cards, _scroll is hidden and previously had
        # nothing else claiming the gallery's stretch=1 leftover height, so
        # cost_label/empty_label used to split it evenly and the dashed
        # empty-state box stretched to a large, mostly-empty rectangle.
        gallery = ReviewGallery()
        gallery.show()
        gallery.resize(900, 700)
        _app.processEvents()
        self.assertLess(gallery.empty_label.height(), 150)

    def test_empty_label_is_vertically_centered_in_leftover_space(self):
        # Follow-up regression test: the compact-box fix above stopped the
        # dashed box itself from stretching, but left a large blank void
        # below it (nothing else claimed the gallery's reserved stretch=1
        # space while empty). Centering the message in that space instead
        # of leaving it pinned to the top makes the void read as
        # intentional rather than as leftover empty space.
        gallery = ReviewGallery()
        gallery.show()
        gallery.resize(900, 700)
        _app.processEvents()
        label_mid = gallery.empty_label.geometry().center().y()
        gallery_mid = gallery.height() / 2
        self.assertAlmostEqual(label_mid, gallery_mid, delta=60)

    def test_empty_label_is_not_clipped_at_wide_window_widths(self):
        # Regression test: AlignHCenter alone let the word-wrapped label size
        # itself to an unreliable "preferred width" heuristic, which at wide
        # window widths produced more/narrower wrapped lines than the
        # label's own height accounted for, clipping the last line(s).
        gallery = ReviewGallery()
        gallery.show()
        gallery.resize(1300, 700)
        _app.processEvents()
        expected_height = gallery.empty_label.heightForWidth(gallery.empty_label.width())
        self.assertGreaterEqual(gallery.empty_label.height(), expected_height)

    def test_empty_state_shows_the_app_logo(self):
        gallery = ReviewGallery()
        self.assertFalse(gallery.logo_label.pixmap().isNull())

    def test_scroll_area_still_gets_full_stretch_when_gallery_has_cards(self):
        # The centering wrapper and the scroll area share stretch=1 in the
        # same layout - only one is ever visible, so the visible one must
        # still claim effectively all the leftover space either way.
        gallery = ReviewGallery()
        gallery.show()
        gallery.resize(900, 700)
        gallery.add_job(_make_job("a.jpg"))
        _app.processEvents()
        self.assertGreater(gallery._scroll.height(), 500)

    def test_empty_label_hidden_after_add_job(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        self.assertTrue(gallery._empty_wrapper.isHidden())

    def test_empty_label_reappears_after_clear(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        gallery.clear()
        self.assertFalse(gallery._empty_wrapper.isHidden())

    def test_empty_label_reappears_after_removing_last_job(self):
        gallery = ReviewGallery()
        gallery.add_job(_make_job("a.jpg"))
        gallery.remove_job("/tmp/a.jpg")
        self.assertFalse(gallery._empty_wrapper.isHidden())

    def test_cost_label_shows_this_run_and_lifetime_totals_independently(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(_Path(d) / "log.jsonl")
            # Historical record unrelated to the current gallery's cards -
            # must count toward lifetime but not toward "this run".
            log.add(DL.DecisionRecord(photo_name="unrelated.jpg", escalated=True, tier="cheap",
                                       provider="openai", cost=0.5, confidence=0.9,
                                       timestamp=1.0))
            gallery = ReviewGallery(decision_log=log)
            job = _make_job("a.jpg")
            job.last_cost = 0.001
            gallery.add_job(job)
            gallery.refresh_cost()
            text = gallery.cost_label.text()
            self.assertIn("0.001", text)
            self.assertIn("0.500", text)

    def test_cost_label_this_run_ignores_cards_without_last_cost(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(_Path(d) / "log.jsonl")
            gallery = ReviewGallery(decision_log=log)
            gallery.add_job(_make_job("a.jpg"))
            gallery.refresh_cost()
            self.assertIn("0.000000", gallery.cost_label.text())


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
            self.assertIn("Estimated cost for escalation: $0.0501", dialog.info_label.text())


from gui.crop_editor_dialog import CropEditorDialog  # noqa: E402


class CropEditorDialogTests(unittest.TestCase):
    def test_dialog_constructs_and_starts_with_no_result(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            Image.new("RGB", (800, 600), (128, 128, 128)).save(src)
            job = P.PhotoJob(src_path=src, filename="a.jpg", shape="square",
                              canvas_long=600, apply_bw=True, apply_grain=True,
                              grain_size="medium", border_size="small")
            job.rendered = Image.new("L", (600, 600), 128)
            dialog = CropEditorDialog(job, inner_ratio=1.0)
            self.assertIsNone(dialog.result_crop_box())

    def test_manual_crop_uses_correct_ratio_for_non_square_source(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            # 4000x3000 source, square (1:1) target shape -> true inner_ratio is 1.0,
            # NOT 0.75 (which is what a buggy fraction-based computation would give)
            Image.new("RGB", (4000, 3000), (100, 150, 200)).save(src)
            job = P.process_photo(src, shape="square", canvas_long=600,
                                   apply_bw=False, apply_grain=True, grain_size="medium", border_size="small")
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
                              canvas_long=600, apply_bw=True, apply_grain=True,
                              grain_size="medium", border_size="small")

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

    def test_saves_color_job_as_color_not_grayscale(self):
        # Regression test: save_kept_jobs used to force every saved photo to
        # "L" mode regardless of job.apply_bw, silently clobbering color
        # output from a bw-off run back to grayscale at save time.
        with tempfile.TemporaryDirectory() as d:
            out_dir = os.path.join(d, "out")
            job = _make_job("a.jpg", keep=True)
            job.apply_bw = False
            job.rendered = Image.new("RGB", (600, 600), (200, 100, 50))
            written = save_kept_jobs([job], out_dir)
            self.assertEqual(len(written), 1)
            with Image.open(written[0]) as saved:
                self.assertEqual(saved.convert("RGB").mode, "RGB")
                r, g, b = saved.convert("RGB").getpixel((0, 0))
                # A true grayscale conversion would collapse r/g/b together;
                # confirm the saved pixel still carries distinct channels.
                self.assertNotEqual((r, g, b), (r, r, r))


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

    def test_output_folder_label_shows_default_before_save(self):
        # Regression test: the default output folder (<input folder>/out)
        # was never shown anywhere in the UI before Save - the user could
        # only discover it by reading the transient post-save status bar
        # message or inspecting the filesystem.
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)
            window.input_panel.folder_edit.setText("/tmp/photos")
            text = window.output_folder_label.text()
            self.assertIn("/tmp/photos/out", text)
            self.assertIn("default", text.lower())

    def test_output_folder_label_reflects_chosen_override(self):
        with tempfile.TemporaryDirectory() as config_dir, \
                tempfile.TemporaryDirectory() as out_dir:
            window = _make_window(config_dir)
            from PySide6.QtWidgets import QFileDialog
            with unittest.mock.patch.object(
                    QFileDialog, "getExistingDirectory", return_value=out_dir):
                window._on_choose_output_clicked()
            text = window.output_folder_label.text()
            self.assertIn(out_dir, text)
            self.assertNotIn("default", text.lower())

    def test_processing_a_folder_populates_the_gallery(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window.input_panel.folder_edit.setText(d)
            window.input_panel.shape_combo.setCurrentText("square")
            window.input_panel.canvas_spin.setValue(600)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 1)

    def test_folder_selected_populates_gallery_with_preview_cards(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d, "b.jpg"), seed=2)
            window = _make_window(config_dir)
            window._on_folder_selected(d)
            window._preview_worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 2)
            self.assertTrue(all(not c.job.processed for c in window.gallery.cards.values()))

    def test_processing_reuses_preview_cards_and_upgrades_them_in_place(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._on_folder_selected(d)
            window._preview_worker.wait(10000)
            _app.processEvents()
            card_before = window.gallery.cards[os.path.join(d, "a.jpg")]

            window._start_processing(d, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()

            self.assertEqual(len(window.gallery.cards), 1)
            card_after = window.gallery.cards[os.path.join(d, "a.jpg")]
            self.assertIs(card_before, card_after)  # same widget, upgraded in place
            self.assertTrue(card_after.job.processed)

    def test_processing_a_different_folder_than_previewed_clears_stale_cards(self):
        with tempfile.TemporaryDirectory() as config_dir, \
                tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            _write_synthetic(os.path.join(d1, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d2, "b.jpg"), seed=2)
            window = _make_window(config_dir)
            window._on_folder_selected(d1)
            window._preview_worker.wait(10000)
            _app.processEvents()

            window._start_processing(d2, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()

            self.assertEqual(list(window.gallery.cards.keys()), [os.path.join(d2, "b.jpg")])

    def test_processing_with_bw_off_produces_color_thumbnail(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, False, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            job = list(window.gallery.cards.values())[0].job
            arr = np.asarray(job.rendered.convert("RGB")).astype(float)
            self.assertGreater(np.abs(arr[..., 0] - arr[..., 1]).mean(), 1.0)

    def test_save_writes_only_kept_jobs(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)
            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(QMessageBox, "information"):
                window._on_save_clicked()
            out_dir = os.path.join(d, "out")
            self.assertTrue(os.path.isdir(out_dir))
            self.assertEqual(len(os.listdir(out_dir)), 1)

    def test_save_shows_durable_confirmation_with_count_and_folder(self):
        # Regression test: the only post-save feedback used to be a transient
        # status-bar message that auto-clears after 5s. Save now needs a
        # durable prompt (a modal, same as the batch-escalation summary)
        # stating how many files were saved and where.
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)

            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(QMessageBox, "information") as mock_info:
                window._on_save_clicked()

            mock_info.assert_called_once()
            msg = mock_info.call_args.args[2]
            self.assertIn("1", msg)
            self.assertIn(window.output_folder(), msg)

    def test_starting_a_new_run_clears_the_previous_gallery(self):
        with tempfile.TemporaryDirectory() as config_dir, \
                tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            _write_synthetic(os.path.join(d1, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d2, "b.jpg"), seed=2)
            window = _make_window(config_dir)
            window._start_processing(d1, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 1)

            window._start_processing(d2, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 2)

            cards = list(window.gallery.cards.values())
            kept_card, other_card = cards[0], cards[1]
            kept_card.keep_checkbox.setChecked(True)
            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(QMessageBox, "information"):
                window._on_save_clicked()

            self.assertNotIn(kept_card.job.src_path, window.gallery.cards)
            self.assertIn(other_card.job.src_path, window.gallery.cards)

    def test_low_confidence_cheap_tier_automatically_escalates_to_strong(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 1)

            QTest.mouseClick(window.clear_button, Qt.LeftButton)

            self.assertEqual(len(window.gallery.cards), 0)

    def test_manual_crop_accept_shows_status_message_and_updates_rendered(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d1, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)

            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(QMessageBox, "question",
                                             return_value=QMessageBox.StandardButton.No) as mock_q:
                window._start_processing(d2, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d1, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)

            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(QMessageBox, "question",
                                             return_value=QMessageBox.StandardButton.Yes):
                window._start_processing(d2, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d1, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()

            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(QMessageBox, "question") as mock_q:
                window._start_processing(d2, "square", 600, True, True, "medium", "small")
                mock_q.assert_not_called()

    def test_busy_indicator_hidden_initially(self):
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)
            self.assertTrue(window.busy_indicator.isHidden())

    def test_start_processing_shows_busy_indicator_until_finished(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
            self.assertFalse(window.busy_indicator.isHidden())
            window._worker.wait(10000)
            _app.processEvents()
            self.assertTrue(window.busy_indicator.isHidden())

    def test_process_button_becomes_stop_while_processing_then_reverts(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
            self.assertEqual(window.input_panel.process_button.text(), "Stop")
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(window.input_panel.process_button.text(), "Process Folder")

    def test_stop_button_halts_worker_and_keeps_partial_results(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            for i in range(5):
                _write_synthetic(os.path.join(d, f"{i}.jpg"), seed=i)
            window = _make_window(config_dir)

            original = P.process_photo

            def slow(*a, **kw):
                time.sleep(0.05)
                return original(*a, **kw)

            with unittest.mock.patch.object(P, "process_photo", side_effect=slow):
                window._start_processing(d, "square", 600, True, True, "medium", "small")
                deadline = time.time() + 10
                while not window.gallery.cards and time.time() < deadline:
                    _app.processEvents()
                    time.sleep(0.01)
                window._on_stop_clicked()
                window._worker.wait(10000)
                _app.processEvents()

            self.assertGreaterEqual(len(window.gallery.cards), 1)
            self.assertLess(len(window.gallery.cards), 5)
            self.assertEqual(window.input_panel.process_button.text(), "Process Folder")
            self.assertTrue(window.busy_indicator.isHidden())

    def test_save_button_disabled_when_nothing_kept(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            self.assertFalse(window.save_button.isEnabled())

    def test_save_button_enables_and_disables_with_keep_checkbox(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)

            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(QMessageBox, "information"):
                window._on_save_clicked()

            self.assertFalse(window.save_button.isEnabled())

    def test_escalate_selected_button_disabled_with_no_selection(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
            window._worker.wait(10000)
            _app.processEvents()
            self.assertFalse(window.escalate_selected_button.isEnabled())

    def test_escalate_selected_button_enables_when_a_card_is_selected(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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

    def test_escalate_single_photo_shows_success_message(self):
        # Regression test: unlike batch escalation (_on_escalate_selected_clicked),
        # single-photo escalation (_on_escalate_requested) never showed any
        # completion message - _on_escalation_done, which runs for both paths,
        # only updates the card and cost header silently.
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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

            import gui.main_window as MW
            from PySide6.QtWidgets import QMessageBox
            with unittest.mock.patch.object(MW.EscalationConfirmDialog, "exec", return_value=None), \
                    unittest.mock.patch.object(MW.EscalationConfirmDialog, "confirmed", return_value=True), \
                    unittest.mock.patch.object(QMessageBox, "information") as mock_info:
                window._on_escalate_requested(job)

            self.assertIn(job.filename, window.statusBar().currentMessage())
            mock_info.assert_called_once()
            self.assertIn(job.filename, mock_info.call_args.args[2])

    def test_escalation_worker_hides_busy_indicator_when_done(self):
        with tempfile.TemporaryDirectory() as config_dir, tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = _make_window(config_dir)
            window._start_processing(d, "square", 600, True, True, "medium", "small")
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


from gui.escalation_history_dialog import EscalationHistoryDialog  # noqa: E402


class EscalationHistoryDialogTests(unittest.TestCase):
    def test_dialog_shows_records_newest_first(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(_Path(d) / "log.jsonl")
            log.add(DL.DecisionRecord(photo_name="a.jpg", escalated=True, tier="cheap",
                                       provider="openai", cost=0.001, confidence=0.9,
                                       timestamp=1.0))
            log.add(DL.DecisionRecord(photo_name="b.jpg", escalated=True, tier="strong",
                                       provider="openai", cost=0.01, confidence=0.5,
                                       timestamp=2.0))
            dialog = EscalationHistoryDialog(log)
            self.assertEqual(dialog.table.rowCount(), 2)
            self.assertEqual(dialog.table.item(0, 0).text(), "b.jpg")
            self.assertEqual(dialog.table.item(1, 0).text(), "a.jpg")

    def test_dialog_with_empty_log_shows_zero_rows(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(_Path(d) / "log.jsonl")
            dialog = EscalationHistoryDialog(log)
            self.assertEqual(dialog.table.rowCount(), 0)


class EscalationHistoryButtonWiringTests(unittest.TestCase):
    def test_escalation_history_button_present(self):
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)
            self.assertIsNotNone(window.escalation_history_button)

    def test_clicking_button_opens_dialog(self):
        with tempfile.TemporaryDirectory() as config_dir:
            window = _make_window(config_dir)

            import gui.main_window as MW

            opened = []

            class FakeDialog:
                def __init__(self, decision_log, parent=None):
                    opened.append(decision_log)

                def exec(self):
                    pass

            with unittest.mock.patch.object(MW, "EscalationHistoryDialog", FakeDialog):
                window._on_escalation_history_clicked()

            self.assertEqual(opened, [window.decision_log])


if __name__ == "__main__":
    unittest.main()
