import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gui.crop_editor_dialog import CropBoxState  # noqa: E402


class CropBoxStateTests(unittest.TestCase):
    def test_h_derived_from_ratio(self):
        state = CropBoxState(img_w=1000, img_h=800, ratio=2.0, x=0, y=0, w=400)
        self.assertEqual(state.h, 200)

    def test_move_by_clamps_to_image_bounds(self):
        state = CropBoxState(img_w=1000, img_h=800, ratio=1.0, x=0, y=0, w=200)
        state.move_by(-50, -50)
        self.assertEqual((state.x, state.y), (0, 0))
        state.move_by(10000, 10000)
        self.assertEqual(state.x, 1000 - 200)
        self.assertEqual(state.y, 800 - 200)

    def test_resize_to_keeps_ratio_and_clamps_to_shorter_dimension(self):
        state = CropBoxState(img_w=1000, img_h=800, ratio=2.0, x=0, y=0, w=400)
        state.resize_to(2000)
        # height would be 2000/2=1000 > img_h=800, so it must clamp on height instead
        self.assertLessEqual(state.h, 800)
        self.assertAlmostEqual(state.w / state.h, 2.0, places=3)

    def test_resize_to_repositions_box_if_it_would_overflow(self):
        state = CropBoxState(img_w=1000, img_h=800, ratio=1.0, x=900, y=0, w=100)
        state.resize_to(300)
        self.assertLessEqual(state.x + state.w, 1000)

    def test_to_crop_box_returns_fractions(self):
        state = CropBoxState(img_w=1000, img_h=800, ratio=1.0, x=100, y=100, w=200)
        box = state.to_crop_box()
        self.assertAlmostEqual(box.x0, 0.1)
        self.assertAlmostEqual(box.y0, 0.125)
        self.assertAlmostEqual(box.x1, 0.3)
        self.assertAlmostEqual(box.y1, 0.375)


if __name__ == "__main__":
    unittest.main()
