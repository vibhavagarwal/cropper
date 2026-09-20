"""OpenAI implementation of the provider-agnostic crop escalation interface.
API shape verified against platform.openai.com docs on 2026-09-20."""
import base64
import json

from openai import OpenAI

from .base import CropProvider, CropDecision

_SCHEMA = {
    "type": "object",
    "properties": {
        "x0": {"type": "number"},
        "y0": {"type": "number"},
        "x1": {"type": "number"},
        "y1": {"type": "number"},
        "confidence": {"type": "number"},
    },
    "required": ["x0", "y0", "x1", "y1", "confidence"],
    "additionalProperties": False,
}

_MODELS = {"cheap": "gpt-4o-mini", "strong": "gpt-6-astra"}

# USD per 1,000,000 tokens: (input, output). Confirmed at platform.openai.com/docs/pricing
# on 2026-09-20 - re-verify before relying on these for a real spend decision much later.
_PRICES = {
    "cheap": (0.15, 0.60),
    "strong": (10.00, 50.00),
}


class OpenAICropProvider(CropProvider):
    def __init__(self, client=None):
        self._client = client if client is not None else OpenAI()

    @property
    def name(self) -> str:
        return "openai"

    def price_per_million_tokens(self, tier: str) -> tuple:
        return _PRICES[tier]

    def request_crop(self, image_bytes: bytes, detection_metadata: dict,
                      inner_ratio: float, tier: str) -> CropDecision:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        prompt = (
            "You are choosing a crop for a travel photo. The crop must have width:height "
            f"ratio {inner_ratio:.4f}. Detection metadata (faces, saliency, symmetry) is "
            f"provided as JSON: {json.dumps(detection_metadata)}. Return the crop box as "
            "fractions of the full image (x0,y0,x1,y1, each 0..1, x1>x0, y1>y0) and your "
            "confidence (0..1) that this is the best composition."
        )
        response = self._client.responses.create(
            model=_MODELS[tier],
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
                ],
            }],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "crop_decision",
                    "schema": _SCHEMA,
                    "strict": True,
                }
            },
        )
        data = json.loads(response.output_text)
        return CropDecision(
            crop_box=(data["x0"], data["y0"], data["x1"], data["y1"]),
            confidence=data["confidence"],
            tier=tier,
        )
