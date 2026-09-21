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

    def __init__(self, folder, shape, canvas_long, apply_bw, apply_grain, grain_size):
        super().__init__()
        self.folder = folder
        self.shape = shape
        self.canvas_long = canvas_long
        self.apply_bw = apply_bw
        self.apply_grain = apply_grain
        self.grain_size = grain_size

    def run(self):
        for job in P.process_folder(self.folder, self.shape, self.canvas_long,
                                     self.apply_bw, self.apply_grain, self.grain_size):
            self.photo_ready.emit(job)
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
