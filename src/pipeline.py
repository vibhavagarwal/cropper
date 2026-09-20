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
    apply_filter: bool
    detection: object = None
    triage_decision: object = None
    crop_box: object = None
    crop_decision: object = None
    rendered: object = None
    keep: bool = False
    error: str = None


_PHOTO_EXTS = {".jpg", ".jpeg"}


def _seed_for(filename: str) -> int:
    return int(hashlib.md5(filename.encode()).hexdigest()[:8], 16)


def render_photo(img, crop_box, shape, canvas_long, apply_filter, seed):
    lay = H.layout(shape, canvas_long)
    iw, ih = lay["inner"]
    x0, y0, x1, y1 = crop_box.to_pixels(img.width, img.height)
    cropped = img.crop((x0, y0, x1, y1)).resize((iw, ih), Image.LANCZOS)
    out = H.emulate(cropped, seed) if apply_filter else cropped.convert("L")
    t = lay["border"]
    canvas = Image.new("L", lay["canvas"], 255)
    canvas.paste(out, (t, t))
    return canvas


def process_photo(src_path: str, shape: str, canvas_long: int, apply_filter: bool) -> PhotoJob:
    filename = os.path.basename(src_path)
    job = PhotoJob(src_path=src_path, filename=filename, shape=shape,
                   canvas_long=canvas_long, apply_filter=apply_filter)
    try:
        img = ImageOps.exif_transpose(Image.open(src_path)).convert("RGB")
        bgr = np.asarray(img)[:, :, ::-1].copy()
        job.detection = det.detect(bgr)
        job.triage_decision = tri.triage(job.detection, img.width * img.height)
        symmetric = job.detection.symmetry_score >= tri.THRESHOLDS["symmetry_ambiguous_high"]
        lay = H.layout(shape, canvas_long)
        job.crop_box = crp.formula_crop(img.width, img.height, lay["inner_ratio"],
                                         job.detection.faces, symmetric)
        seed = _seed_for(filename)
        job.rendered = render_photo(img, job.crop_box, shape, canvas_long, apply_filter, seed)
    except Exception as e:  # noqa: BLE001 - a single bad photo must not stop the batch
        job.error = str(e)
    return job


def process_folder(folder: str, shape: str, canvas_long: int, apply_filter: bool):
    paths = sorted(
        p for p in glob.glob(os.path.join(folder, "*"))
        if os.path.splitext(p)[1].lower() in _PHOTO_EXTS
    )
    for p in paths:
        yield process_photo(p, shape, canvas_long, apply_filter)


def apply_escalation(job: PhotoJob, provider, tier: str) -> PhotoJob:
    img = ImageOps.exif_transpose(Image.open(job.src_path)).convert("RGB")
    lay = H.layout(job.shape, job.canvas_long)
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
    job.crop_box = crp.CropBox(x0, y0, x1, y1)
    seed = _seed_for(job.filename)
    job.rendered = render_photo(img, job.crop_box, job.shape, job.canvas_long,
                                 job.apply_filter, seed)
    return job


def apply_manual_crop(job: PhotoJob, crop_box) -> PhotoJob:
    img = ImageOps.exif_transpose(Image.open(job.src_path)).convert("RGB")
    seed = _seed_for(job.filename)
    job.crop_box = crop_box
    job.rendered = render_photo(img, crop_box, job.shape, job.canvas_long,
                                 job.apply_filter, seed)
    return job
