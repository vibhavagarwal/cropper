"""QThread workers wrapping pipeline calls so the GUI event loop never blocks
on image processing or a network call."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import QThread, Signal

import pipeline as P


class ProcessFolderWorker(QThread):
    photo_ready = Signal(object)
    finished_all = Signal()

    def __init__(self, folder, shape, canvas_long, apply_bw, apply_grain, grain_size,
                 border_size, look=""):
        super().__init__()
        self.folder = folder
        self.shape = shape
        self.canvas_long = canvas_long
        self.apply_bw = apply_bw
        self.apply_grain = apply_grain
        self.grain_size = grain_size
        self.border_size = border_size
        self.moodportrait = look == "moodportrait"
        self._stop_requested = False

    def stop(self):
        # Cooperative: lets the photo currently being processed finish (and
        # still get emitted/kept) rather than being interrupted mid-work;
        # only the photos after it are skipped.
        self._stop_requested = True

    def run(self):
        for path in P.list_photo_paths(self.folder):
            if self._stop_requested:
                break
            job = P.process_photo(path, self.shape, self.canvas_long, self.apply_bw,
                                   self.apply_grain, self.grain_size, self.border_size,
                                   self.moodportrait)
            self.photo_ready.emit(job)
        self.finished_all.emit()


class FolderPreviewWorker(QThread):
    preview_ready = Signal(object)
    finished_all = Signal()

    def __init__(self, folder, shape, canvas_long, apply_bw, apply_grain, grain_size,
                 border_size, look=""):
        super().__init__()
        self.folder = folder
        self.shape = shape
        self.canvas_long = canvas_long
        self.apply_bw = apply_bw
        self.apply_grain = apply_grain
        self.grain_size = grain_size
        self.border_size = border_size
        self.moodportrait = look == "moodportrait"

    def run(self):
        for path in P.list_photo_paths(self.folder):
            job = P.load_preview(path, self.shape, self.canvas_long, self.apply_bw,
                                  self.apply_grain, self.grain_size, self.border_size)
            self.preview_ready.emit(job)
        self.finished_all.emit()


class EscalationWorker(QThread):
    photo_updated = Signal(object)
    error = Signal(str)

    def __init__(self, job, provider, tier):
        super().__init__()
        self.job = job
        self.provider = provider
        self.tier = tier

    def run(self):
        try:
            updated = P.apply_escalation(self.job, self.provider, self.tier)
            self.photo_updated.emit(updated)
        except Exception as e:  # noqa: BLE001 - surfaced to the GUI via the error signal
            self.error.emit(str(e))
