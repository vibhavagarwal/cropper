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


if __name__ == "__main__":
    unittest.main()
