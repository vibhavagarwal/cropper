import os
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import detection as D  # noqa: E402


def synthetic_symmetric(w=200, h=160):
    img = np.zeros((h, w), dtype=np.uint8)
    half = w // 2
    ramp = np.linspace(0, 255, half, dtype=np.uint8)
    img[:, :half] = ramp[None, :]
    img[:, half:half + half] = ramp[None, ::-1][:, :img[:, half:].shape[1]]
    return img


def synthetic_asymmetric(w=200, h=160):
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, size=(h, w), dtype=np.uint8)


class SymmetryTests(unittest.TestCase):
    def test_symmetric_image_scores_high(self):
        self.assertGreater(D.symmetry_score(synthetic_symmetric()), 0.9)

    def test_random_image_scores_lower(self):
        sym = D.symmetry_score(synthetic_symmetric())
        rand = D.symmetry_score(synthetic_asymmetric())
        self.assertLess(rand, sym)


class SaliencyTests(unittest.TestCase):
    def test_saliency_map_shape_and_range(self):
        bgr = np.zeros((120, 160, 3), dtype=np.uint8)
        bgr[40:80, 60:100] = 255
        result = D.saliency_map(bgr)
        self.assertEqual(result.heatmap.shape, (120, 160))
        self.assertTrue((result.heatmap >= 0).all() and (result.heatmap <= 1).all())
        self.assertIsInstance(result.blob_fraction, float)
        self.assertIsInstance(result.touches_edge, bool)

    def test_whole_frame_bright_blob_touches_edge(self):
        bgr = np.full((100, 100, 3), 255, dtype=np.uint8)
        result = D.saliency_map(bgr, blob_threshold=0.1)
        self.assertTrue(result.touches_edge)


class FaceDetectionTests(unittest.TestCase):
    def test_no_faces_in_blank_image(self):
        bgr = np.zeros((200, 200, 3), dtype=np.uint8)
        self.assertEqual(D.detect_faces(bgr), [])

    def test_no_faces_on_repetitive_textured_background(self):
        # Regression test: the Haar cascade this replaced false-positived
        # heavily on repetitive/textured non-face patterns (e.g. a pegboard
        # of holes) - a checkerboard-of-dots pattern approximates that here.
        # See .scratch/face-detection-tuning/issues/01-...md.
        h, w = 400, 400
        bgr = np.full((h, w, 3), 180, dtype=np.uint8)
        for cy in range(20, h, 40):
            for cx in range(20, w, 40):
                cv2.circle(bgr, (cx, cy), 8, (40, 40, 40), -1)
        self.assertEqual(D.detect_faces(bgr), [])

    def test_no_faces_on_random_noise(self):
        rng = np.random.default_rng(0)
        bgr = rng.integers(0, 256, size=(300, 300, 3), dtype=np.uint8)
        self.assertEqual(D.detect_faces(bgr), [])


class DetectTests(unittest.TestCase):
    def test_detect_returns_full_result(self):
        bgr = np.zeros((120, 160, 3), dtype=np.uint8)
        result = D.detect(bgr)
        self.assertIsInstance(result, D.DetectionResult)
        self.assertIsInstance(result.faces, list)
        self.assertIsInstance(result.saliency, D.SaliencyResult)
        self.assertIsInstance(result.symmetry_score, float)


if __name__ == "__main__":
    unittest.main()
