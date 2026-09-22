"""Per-photo pipeline orchestration for the free/local stages (EXIF correction,
detection, triage, formula crop, filter, border) plus the explicit, separately
triggered paid escalation and manual-crop-override paths."""
import glob
import hashlib
import io
import os
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

import crop as crp
import detection as det
import hp5_emulate as H
import triage as tri


@dataclass
class PhotoJob:
    src_path: str
    filename: str
    shape: str
    canvas_long: int
    apply_bw: bool
    apply_grain: bool
    grain_size: str
    border_size: str
    detection: object = None
    triage_decision: object = None
    crop_box: object = None
    crop_decision: object = None
    rendered: object = None
    keep: bool = False
    error: str = None
    # False only for a raw folder-preview card shown before Process Folder
    # actually runs it - every real pipeline output defaults to processed.
    processed: bool = True


_PHOTO_EXTS = {".jpg", ".jpeg"}


def _seed_for(filename: str) -> int:
    return int(hashlib.md5(filename.encode()).hexdigest()[:8], 16)


def render_photo(img, crop_box, shape, canvas_long, apply_bw, apply_grain, grain_size,
                  border_size, seed):
    lay = H.layout(shape, canvas_long, border_size=border_size)
    iw, ih = lay["inner"]
    x0, y0, x1, y1 = crop_box.to_pixels(img.width, img.height)
    cropped = img.crop((x0, y0, x1, y1)).resize((iw, ih), Image.LANCZOS)
    out = H.emulate(cropped, seed, apply_bw=apply_bw, apply_grain=apply_grain,
                     grain_size=grain_size)
    t = lay["border"]
    mode = "L" if apply_bw else "RGB"
    white = 255 if apply_bw else (255, 255, 255)
    canvas = Image.new(mode, lay["canvas"], white)
    canvas.paste(out, (t, t))
    return canvas


def process_photo(src_path: str, shape: str, canvas_long: int, apply_bw: bool,
                   apply_grain: bool, grain_size: str, border_size: str) -> PhotoJob:
    filename = os.path.basename(src_path)
    job = PhotoJob(src_path=src_path, filename=filename, shape=shape,
                   canvas_long=canvas_long, apply_bw=apply_bw, apply_grain=apply_grain,
                   grain_size=grain_size, border_size=border_size)
    try:
        img = ImageOps.exif_transpose(Image.open(src_path)).convert("RGB")
        bgr = np.asarray(img)[:, :, ::-1].copy()
        job.detection = det.detect(bgr)
        job.triage_decision = tri.triage(job.detection, img.width * img.height)
        symmetric = job.detection.symmetry_score >= tri.THRESHOLDS["symmetry_ambiguous_high"]
        lay = H.layout(shape, canvas_long, border_size=border_size)
        job.crop_box = crp.formula_crop(img.width, img.height, lay["inner_ratio"],
                                         job.detection.faces, symmetric)
        seed = _seed_for(filename)
        job.rendered = render_photo(img, job.crop_box, shape, canvas_long,
                                     apply_bw, apply_grain, grain_size, border_size, seed)
    except Exception as e:  # noqa: BLE001 - a single bad photo must not stop the batch
        job.error = str(e)
    return job


def list_photo_paths(folder: str):
    return sorted(
        p for p in glob.glob(os.path.join(folder, "*"))
        if os.path.splitext(p)[1].lower() in _PHOTO_EXTS
    )


def process_folder(folder: str, shape: str, canvas_long: int, apply_bw: bool,
                    apply_grain: bool, grain_size: str, border_size: str):
    for p in list_photo_paths(folder):
        yield process_photo(p, shape, canvas_long, apply_bw, apply_grain, grain_size,
                             border_size)


_PREVIEW_THUMB_MAX = 640


def load_preview(src_path: str, shape: str, canvas_long: int, apply_bw: bool,
                  apply_grain: bool, grain_size: str, border_size: str) -> PhotoJob:
    """Raw, unprocessed preview: EXIF-corrected original, downscaled for a
    cheap thumbnail, no detection/triage/crop/render. shape/canvas_long/etc.
    are carried along for consistency with a processed PhotoJob but unused
    while processed=False."""
    filename = os.path.basename(src_path)
    job = PhotoJob(src_path=src_path, filename=filename, shape=shape,
                   canvas_long=canvas_long, apply_bw=apply_bw, apply_grain=apply_grain,
                   grain_size=grain_size, border_size=border_size, processed=False)
    try:
        img = ImageOps.exif_transpose(Image.open(src_path)).convert("RGB")
        img.thumbnail((_PREVIEW_THUMB_MAX, _PREVIEW_THUMB_MAX))
        job.rendered = img
    except Exception as e:  # noqa: BLE001 - a single bad photo must not stop the batch
        job.error = str(e)
    return job


def _correct_crop_ratio(crop_box: "crp.CropBox", img_w: int, img_h: int,
                         inner_ratio: float, tol: float = 0.005) -> "crp.CropBox":
    """Adjust crop_box so its pixel-space aspect ratio matches inner_ratio,
    keeping its center fixed. AI-provided crop boxes are not guaranteed to
    be on-ratio the way formula_crop's are by construction; render_photo
    resizes whatever box it's given to a fixed inner size, so an off-ratio
    box would otherwise be squeeze-stretched rather than cleanly cropped."""
    x0, y0, x1, y1 = crop_box.to_pixels(img_w, img_h)
    crop_w, crop_h = x1 - x0, y1 - y0
    if crop_w <= 0 or crop_h <= 0:
        return crop_box
    ratio = crop_w / crop_h
    if abs(ratio - inner_ratio) <= tol:
        return crop_box

    center_x, center_y = (x0 + x1) / 2, (y0 + y1) / 2
    if ratio > inner_ratio:
        new_w, new_h = round(crop_h * inner_ratio), crop_h
    else:
        new_w, new_h = crop_w, round(crop_w / inner_ratio)
    new_w = min(new_w, img_w)
    new_h = min(new_h, img_h)

    left = max(0, min(center_x - new_w / 2, img_w - new_w))
    top = max(0, min(center_y - new_h / 2, img_h - new_h))
    return crp.CropBox(
        x0=left / img_w, y0=top / img_h,
        x1=(left + new_w) / img_w, y1=(top + new_h) / img_h,
    )


def apply_escalation(job: PhotoJob, provider, tier: str) -> PhotoJob:
    img = ImageOps.exif_transpose(Image.open(job.src_path)).convert("RGB")
    lay = H.layout(job.shape, job.canvas_long, border_size=job.border_size)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    metadata = {
        "faces": [dict(x=f.x, y=f.y, w=f.w, h=f.h) for f in job.detection.faces],
        "saliency_blob_fraction": job.detection.saliency.blob_fraction,
        "symmetry_score": job.detection.symmetry_score,
    }
    decision = provider.request_crop(buf.getvalue(), metadata, lay["inner_ratio"], tier)
    job.crop_decision = decision
    x0, y0, x1, y1 = decision.crop_box
    job.crop_box = _correct_crop_ratio(crp.CropBox(x0, y0, x1, y1), img.width, img.height,
                                        lay["inner_ratio"])
    seed = _seed_for(job.filename)
    job.rendered = render_photo(img, job.crop_box, job.shape, job.canvas_long,
                                 job.apply_bw, job.apply_grain, job.grain_size,
                                 job.border_size, seed)
    return job


def apply_manual_crop(job: PhotoJob, crop_box) -> PhotoJob:
    img = ImageOps.exif_transpose(Image.open(job.src_path)).convert("RGB")
    seed = _seed_for(job.filename)
    job.crop_box = crop_box
    job.rendered = render_photo(img, crop_box, job.shape, job.canvas_long,
                                 job.apply_bw, job.apply_grain, job.grain_size,
                                 job.border_size, seed)
    return job
