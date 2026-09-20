import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import cost as C  # noqa: E402


class FakeProvider:
    def price_per_million_tokens(self, tier):
        return {"cheap": (0.15, 0.60), "strong": (10.00, 50.00)}[tier]


class CostTests(unittest.TestCase):
    def test_call_cost_is_positive_and_scales_with_tier(self):
        provider = FakeProvider()
        cheap = C.estimate_call_cost(provider, "cheap")
        strong = C.estimate_call_cost(provider, "strong")
        self.assertGreater(cheap, 0)
        self.assertGreater(strong, cheap)

    def test_worst_case_batch_cost_assumes_strong_tier_for_every_photo(self):
        provider = FakeProvider()
        single_strong = C.estimate_call_cost(provider, "strong")
        batch = C.estimate_worst_case_batch_cost(provider, 5)
        self.assertAlmostEqual(batch, 5 * single_strong)

    def test_zero_flagged_photos_costs_nothing(self):
        provider = FakeProvider()
        self.assertEqual(C.estimate_worst_case_batch_cost(provider, 0), 0.0)


if __name__ == "__main__":
    unittest.main()
