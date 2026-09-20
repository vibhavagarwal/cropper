import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import triage as T  # noqa: E402
from detection import DetectionResult, FaceBox, SaliencyResult  # noqa: E402


def make_detection(faces=None, blob_fraction=0.1, touches_edge=False, symmetry_score=0.95):
    import numpy as np
    return DetectionResult(
        faces=faces or [],
        saliency=SaliencyResult(heatmap=np.zeros((10, 10), dtype="float32"),
                                 blob_fraction=blob_fraction, touches_edge=touches_edge),
        symmetry_score=symmetry_score,
    )


class TriageTests(unittest.TestCase):
    def test_clear_photo_does_not_escalate(self):
        d = make_detection(faces=[FaceBox(10, 10, 50, 50)], blob_fraction=0.1,
                            touches_edge=False, symmetry_score=0.95)
        decision = T.triage(d, image_area=100 * 100)
        self.assertFalse(decision.escalate)
        self.assertEqual(decision.reasons, [])

    def test_whole_frame_saliency_escalates(self):
        d = make_detection(blob_fraction=0.9)
        decision = T.triage(d, image_area=100 * 100)
        self.assertTrue(decision.escalate)
        self.assertIn("saliency spans nearly the whole frame", decision.reasons)

    def test_multiple_faces_no_clear_primary_escalates(self):
        d = make_detection(faces=[FaceBox(0, 0, 50, 50), FaceBox(60, 60, 48, 48)])
        decision = T.triage(d, image_area=100 * 100)
        self.assertTrue(decision.escalate)
        self.assertIn("multiple faces with no clear primary subject", decision.reasons)

    def test_multiple_faces_with_clear_primary_does_not_escalate_for_that_reason(self):
        d = make_detection(faces=[FaceBox(0, 0, 80, 80), FaceBox(90, 90, 10, 10)])
        decision = T.triage(d, image_area=100 * 100)
        self.assertNotIn("multiple faces with no clear primary subject", decision.reasons)

    def test_edge_touching_blob_escalates(self):
        d = make_detection(touches_edge=True)
        decision = T.triage(d, image_area=100 * 100)
        self.assertTrue(decision.escalate)
        self.assertIn("saliency blob touches an edge or corner", decision.reasons)

    def test_ambiguous_symmetry_escalates(self):
        d = make_detection(symmetry_score=0.65)
        decision = T.triage(d, image_area=100 * 100)
        self.assertTrue(decision.escalate)
        self.assertIn("symmetry score is ambiguous", decision.reasons)

    def test_decisive_low_symmetry_does_not_escalate_for_that_reason(self):
        d = make_detection(symmetry_score=0.1)
        decision = T.triage(d, image_area=100 * 100)
        self.assertNotIn("symmetry score is ambiguous", decision.reasons)


if __name__ == "__main__":
    unittest.main()
