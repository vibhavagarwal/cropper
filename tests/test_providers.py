import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from providers.base import CropProvider, CropDecision  # noqa: E402


class DummyProvider(CropProvider):
    @property
    def name(self):
        return "dummy"

    def price_per_million_tokens(self, tier):
        return (1.0, 2.0)

    def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
        return CropDecision(crop_box=(0.1, 0.1, 0.9, 0.9), confidence=0.8, tier=tier)


class CropProviderInterfaceTests(unittest.TestCase):
    def test_cannot_instantiate_abstract_base(self):
        with self.assertRaises(TypeError):
            CropProvider()

    def test_concrete_provider_implements_interface(self):
        p = DummyProvider()
        self.assertEqual(p.name, "dummy")
        self.assertEqual(p.price_per_million_tokens("cheap"), (1.0, 2.0))
        decision = p.request_crop(b"", {}, 0.8, "cheap")
        self.assertEqual(decision.tier, "cheap")
        self.assertEqual(decision.crop_box, (0.1, 0.1, 0.9, 0.9))


if __name__ == "__main__":
    unittest.main()
