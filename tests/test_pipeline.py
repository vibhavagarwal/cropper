import glob
import hashlib
import io
import os
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pipeline as P  # noqa: E402
from crop import CropBox  # noqa: E402
from providers.base import CropDecision  # noqa: E402


def synthetic_jpeg(path, w=800, h=600, seed=0):
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 255, w, dtype=np.float32)[None, :].repeat(h, 0)
    rgb = np.stack([x, x[::-1], np.full_like(x, 128)], -1) + rng.normal(0, 3, (h, w, 3))
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(path, quality=95)


class ProcessPhotoTests(unittest.TestCase):
    def test_process_photo_produces_rendered_image_matching_canvas_size(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            synthetic_jpeg(src)
            job = P.process_photo(src, shape="landscape", canvas_long=1200, apply_filter=True)
            self.assertIsNone(job.error)
            self.assertIsNotNone(job.rendered)
            import hp5_emulate as H
            self.assertEqual(job.rendered.size, H.layout("landscape", 1200)["canvas"])

    def test_process_photo_without_filter_skips_emulation(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            synthetic_jpeg(src)
            job = P.process_photo(src, shape="square", canvas_long=800, apply_filter=False)
            self.assertIsNone(job.error)
            self.assertEqual(job.rendered.mode, "L")

    def test_process_photo_sets_error_on_bad_file(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "not_an_image.jpg")
            with open(src, "wb") as f:
                f.write(b"not a jpeg")
            job = P.process_photo(src, shape="square", canvas_long=800, apply_filter=True)
            self.assertIsNotNone(job.error)
            self.assertIsNone(job.rendered)


class ProcessFolderTests(unittest.TestCase):
    def test_process_folder_yields_one_job_per_photo_and_skips_bad_ones(self):
        with tempfile.TemporaryDirectory() as d:
            synthetic_jpeg(os.path.join(d, "a.jpg"), seed=1)
            synthetic_jpeg(os.path.join(d, "b.jpg"), seed=2)
            with open(os.path.join(d, "c.jpg"), "wb") as f:
                f.write(b"corrupt")
            jobs = list(P.process_folder(d, shape="square", canvas_long=600, apply_filter=True))
            self.assertEqual(len(jobs), 3)
            errored = [j for j in jobs if j.error]
            ok = [j for j in jobs if not j.error]
            self.assertEqual(len(errored), 1)
            self.assertEqual(len(ok), 2)


class EscalationAndManualCropTests(unittest.TestCase):
    def test_apply_escalation_updates_crop_and_rerenders(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            synthetic_jpeg(src)
            job = P.process_photo(src, shape="square", canvas_long=600, apply_filter=True)
            original_rendered = job.rendered

            class FakeProvider:
                def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
                    return CropDecision(crop_box=(0.1, 0.1, 0.9, 0.9), confidence=0.77, tier=tier)

            updated = P.apply_escalation(job, FakeProvider(), "strong")
            self.assertEqual(updated.crop_decision.confidence, 0.77)
            self.assertEqual(updated.crop_decision.tier, "strong")
            self.assertIsNotNone(updated.rendered)
            self.assertNotEqual(np.asarray(updated.rendered).tobytes(),
                                 np.asarray(original_rendered).tobytes())

    def test_apply_manual_crop_rerenders_with_given_box(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            synthetic_jpeg(src)
            job = P.process_photo(src, shape="square", canvas_long=600, apply_filter=True)
            box = CropBox(0.0, 0.0, 1.0, 1.0)
            updated = P.apply_manual_crop(job, box)
            self.assertEqual(updated.crop_box, box)
            self.assertIsNotNone(updated.rendered)


if __name__ == "__main__":
    unittest.main()
