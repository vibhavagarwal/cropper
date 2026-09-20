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


import json
from unittest.mock import MagicMock

from providers.openai_provider import OpenAICropProvider  # noqa: E402


class FakeResponses:
    def __init__(self, payload):
        self._payload = payload
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        response = MagicMock()
        response.output_text = json.dumps(self._payload)
        return response


class FakeOpenAIClient:
    def __init__(self, payload):
        self.responses = FakeResponses(payload)


class OpenAICropProviderTests(unittest.TestCase):
    def test_name(self):
        provider = OpenAICropProvider(client=FakeOpenAIClient({}))
        self.assertEqual(provider.name, "openai")

    def test_pricing_cheap_and_strong_differ(self):
        provider = OpenAICropProvider(client=FakeOpenAIClient({}))
        cheap = provider.price_per_million_tokens("cheap")
        strong = provider.price_per_million_tokens("strong")
        self.assertLess(cheap[0], strong[0])
        self.assertLess(cheap[1], strong[1])

    def test_request_crop_parses_response_into_crop_decision(self):
        payload = {"x0": 0.1, "y0": 0.2, "x1": 0.9, "y1": 0.8, "confidence": 0.73}
        fake_client = FakeOpenAIClient(payload)
        provider = OpenAICropProvider(client=fake_client)
        decision = provider.request_crop(b"fakejpegbytes", {"faces": []}, 0.8, "cheap")
        self.assertEqual(decision.crop_box, (0.1, 0.2, 0.9, 0.8))
        self.assertAlmostEqual(decision.confidence, 0.73)
        self.assertEqual(decision.tier, "cheap")

    def test_request_crop_sends_image_and_json_schema(self):
        payload = {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 1.0, "confidence": 0.5}
        fake_client = FakeOpenAIClient(payload)
        provider = OpenAICropProvider(client=fake_client)
        provider.request_crop(b"fakejpegbytes", {"faces": []}, 0.8, "strong")
        kwargs = fake_client.responses.last_call_kwargs
        self.assertEqual(kwargs["model"], "gpt-6-astra")
        content = kwargs["input"][0]["content"]
        self.assertTrue(any(c["type"] == "input_image" for c in content))
        self.assertEqual(kwargs["text"]["format"]["type"], "json_schema")
        self.assertTrue(kwargs["text"]["format"]["strict"])


if __name__ == "__main__":
    unittest.main()
