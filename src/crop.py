"""Formula crop: rule-of-thirds and symmetry math for non-escalated photos.
Subject position is computed as an exact fraction of the crop and checked
against the 1/3 and 2/3 targets - not eyeballed. Symmetric subjects (e.g. a
centered facade) are centered instead of placed on a thirds line."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CropBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def to_pixels(self, img_w: int, img_h: int) -> tuple:
        return (round(self.x0 * img_w), round(self.y0 * img_h),
                round(self.x1 * img_w), round(self.y1 * img_h))


def _subject_center_px(img_w: int, img_h: int, faces: list) -> tuple:
    if not faces:
        return (img_w / 2, img_h / 2)
    best = max(faces, key=lambda f: f.area)
    return (best.x + best.w / 2, best.y + best.h / 2)


def formula_crop(img_w: int, img_h: int, inner_ratio: float, faces: list, symmetric: bool) -> CropBox:
    src_ratio = img_w / img_h
    if src_ratio > inner_ratio:
        crop_h = img_h
        crop_w = round(crop_h * inner_ratio)
    else:
        crop_w = img_w
        crop_h = round(crop_w / inner_ratio)

    if symmetric:
        center_x_px, center_y_px = img_w / 2, img_h / 2
        target_x, target_y = 0.5, 0.5
    else:
        center_x_px, center_y_px = _subject_center_px(img_w, img_h, faces)
        target_x = 1 / 3 if center_x_px < img_w / 2 else 2 / 3
        target_y = 1 / 3 if center_y_px < img_h / 2 else 2 / 3

    left = center_x_px - target_x * crop_w
    top = center_y_px - target_y * crop_h
    left = max(0, min(left, img_w - crop_w))
    top = max(0, min(top, img_h - crop_h))

    return CropBox(
        x0=left / img_w, y0=top / img_h,
        x1=(left + crop_w) / img_w, y1=(top + crop_h) / img_h,
    )
