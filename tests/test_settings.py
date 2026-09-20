import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import settings as S  # noqa: E402


class AppSettingsTests(unittest.TestCase):
    def test_load_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            loaded = S.AppSettings.load(Path(d) / "missing.json")
            self.assertEqual(loaded.shape, "square")
            self.assertEqual(loaded.canvas_long, 2400)
            self.assertTrue(loaded.apply_filter)

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            original = S.AppSettings(shape="portrait", canvas_long=1800, apply_filter=False,
                                      last_input_folder="C:/photos", last_output_folder="C:/out")
            original.save(path)
            loaded = S.AppSettings.load(path)
            self.assertEqual(loaded, original)

    def test_load_ignores_unknown_fields_gracefully(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            path.write_text('{"shape": "landscape", "canvas_long": 3000, "extra_junk": 1}',
                             encoding="utf-8")
            loaded = S.AppSettings.load(path)
            self.assertEqual(loaded.shape, "landscape")
            self.assertEqual(loaded.canvas_long, 3000)


if __name__ == "__main__":
    unittest.main()
