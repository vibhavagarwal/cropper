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


if __name__ == "__main__":
    unittest.main()
