"""Main window: wired up incrementally through Tasks 13-21."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import QMainWindow

from settings import AppSettings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cropper")
        self.settings_path = Path.home() / ".cropper" / "settings.json"
        self.settings = AppSettings.load(self.settings_path)
