"""Provider-agnostic interface for the escalated crop decision: one combined
call per photo, image + detection metadata in, crop decision + confidence out.
Any vision-capable model with structured/JSON output can implement this."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CropDecision:
    crop_box: tuple  # (x0, y0, x1, y1) as fractions of image width/height, 0..1
    confidence: float  # 0..1
    tier: str  # "cheap" or "strong"


class CropProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def price_per_million_tokens(self, tier: str) -> tuple:
        """Return (input_price, output_price) in USD per 1,000,000 tokens for this tier."""
        ...

    @abstractmethod
    def request_crop(self, image_bytes: bytes, detection_metadata: dict,
                      inner_ratio: float, tier: str) -> CropDecision:
        ...
