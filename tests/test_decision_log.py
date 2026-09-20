# tests/test_decision_log.py
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import decision_log as DL  # noqa: E402


class DecisionLogTests(unittest.TestCase):
    def test_new_log_starts_empty(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(Path(d) / "log.jsonl")
            self.assertEqual(log.records, [])
            self.assertEqual(log.running_cost, 0.0)

    def test_add_appends_and_persists(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "log.jsonl"
            log = DL.DecisionLog(path)
            record = DL.DecisionRecord(photo_name="a.jpg", escalated=True, tier="cheap",
                                        provider="openai", cost=0.001, confidence=0.9,
                                        timestamp=1.0)
            log.add(record)
            self.assertEqual(len(log.records), 1)
            self.assertAlmostEqual(log.running_cost, 0.001)
            self.assertTrue(path.exists())

    def test_reloading_reads_previous_records(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "log.jsonl"
            log1 = DL.DecisionLog(path)
            log1.add(DL.DecisionRecord(photo_name="a.jpg", escalated=False, tier="",
                                        provider="", cost=0.0, confidence=-1.0, timestamp=1.0))
            log1.add(DL.DecisionRecord(photo_name="b.jpg", escalated=True, tier="strong",
                                        provider="openai", cost=0.05, confidence=0.4,
                                        timestamp=2.0))
            log2 = DL.DecisionLog(path)
            self.assertEqual(len(log2.records), 2)
            self.assertAlmostEqual(log2.running_cost, 0.05)


if __name__ == "__main__":
    unittest.main()
