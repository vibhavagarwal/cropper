import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import crop as C  # noqa: E402
from detection import FaceBox  # noqa: E402


class CropBoxTests(unittest.TestCase):
    def test_to_pixels(self):
        box = C.CropBox(0.25, 0.25, 0.75, 0.75)
        self.assertEqual(box.to_pixels(400, 200), (100, 50, 300, 150))


class FormulaCropTests(unittest.TestCase):
    def test_crop_ratio_matches_inner_ratio(self):
        box = C.formula_crop(4000, 3000, inner_ratio=0.7917, faces=[], symmetric=False)
        x0, y0, x1, y1 = box.to_pixels(4000, 3000)
        w, h = x1 - x0, y1 - y0
        self.assertAlmostEqual(w / h, 0.7917, delta=0.005)

    def test_no_face_centers_on_image(self):
        box = C.formula_crop(1000, 1000, inner_ratio=1.0, faces=[], symmetric=False)
        x0, y0, x1, y1 = box.to_pixels(1000, 1000)
        self.assertAlmostEqual((x0 + x1) / 2, 500, delta=1)
        self.assertAlmostEqual((y0 + y1) / 2, 500, delta=1)

    def test_symmetric_subject_is_centered_regardless_of_face_position(self):
        faces = [FaceBox(100, 100, 50, 50)]
        box = C.formula_crop(1000, 1000, inner_ratio=1.0, faces=faces, symmetric=True)
        x0, y0, x1, y1 = box.to_pixels(1000, 1000)
        self.assertAlmostEqual((x0 + x1) / 2, 500, delta=1)
        self.assertAlmostEqual((y0 + y1) / 2, 500, delta=1)

    def test_off_center_face_pulls_crop_toward_a_third_line(self):
        # 1500x1000 image, square crop (inner_ratio=1.0) leaves 500px of horizontal
        # slack (crop_w=1000 < img_w=1500) for the crop to actually shift - a square
        # crop of a square image would have zero slack on either axis and could
        # never be off-center regardless of face position, so this must be
        # rectangular for the test to be satisfiable at all.
        faces = [FaceBox(50, 450, 100, 100)]  # face in the left portion of the frame
        box = C.formula_crop(1500, 1000, inner_ratio=1.0, faces=faces, symmetric=False)
        x0, y0, x1, y1 = box.to_pixels(1500, 1000)
        crop_center_x = (x0 + x1) / 2
        self.assertLess(crop_center_x, 750)  # not centered on the full 1500-wide image

    def test_crop_stays_within_source_bounds(self):
        faces = [FaceBox(0, 0, 20, 20)]
        box = C.formula_crop(1000, 800, inner_ratio=0.8, faces=faces, symmetric=False)
        x0, y0, x1, y1 = box.to_pixels(1000, 800)
        self.assertGreaterEqual(x0, 0)
        self.assertGreaterEqual(y0, 0)
        self.assertLessEqual(x1, 1000)
        self.assertLessEqual(y1, 800)


if __name__ == "__main__":
    unittest.main()
