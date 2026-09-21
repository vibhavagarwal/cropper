#!/usr/bin/env python3
"""
hp5_emulate.py

Post-hoc emulation of the "Ilford HP5 Plus 400" Fujifilm recipe (Anders Lindborg,
via Fuji X Weekly) on already-shot colour JPEGs.

Recipe being imitated:
  Monochrome, DR400, Highlight -1, Shadow +1, NR -4, Sharpness -2, Clarity 0,
  Grain Strong/Large, Daylight WB +1 Red / -8 Blue.

Pipeline (all deterministic; grain is seeded per file so reruns are identical):
  1. EXIF orientation fix
  2. Optional downscale (--max-edge)
  3. WB shift emulation: red gain up, blue gain down, before the gray mix
  4. Gray conversion (weighted channel mix)
  5. Tone curve: slight toe, soft highlight shoulder (DR400 / Highlight -1),
     lifted black floor (~8/255, matches the reference samples)
  6. Slight softening (Sharpness -2, NR -4 means no denoise)
  7. Grain: size is a fraction of the long edge, so the look is resolution independent.
     Apply AFTER the final crop/resize and BEFORE the border.
  8. Border (add_border): white, uniform, applied last so it stays clean.

Fixed-size mode (--shape): crop to the INNER ratio, resize, filter, then border, so the
output is exactly the canvas size (square 1:1, portrait 4:5, landscape 5:4) with no distortion.

Every number below is a tunable guess except the black floor, which was measured
from the four reference images (0.5th percentile = 6 to 9 of 255).
"""
import argparse
import hashlib
import os
import sys

import numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import gaussian_filter, zoom

# ---------------------------------------------------------------- parameters
PARAMS = dict(
    # White balance shift as channel gains (Daylight, +1 R, -8 B)
    wb_r=1.03,
    wb_g=1.00,
    wb_b=0.80,
    # Gray mix (renormalised after WB gains). Rec.601 luma to start.
    mix_r=0.299,
    mix_g=0.587,
    mix_b=0.114,
    # Tone curve
    toe_gamma=1.08,      # >1 deepens shadows slightly (Shadow +1)
    knee=0.45,           # where the highlight shoulder starts (Highlight -1, DR400)
    ceiling=0.80,        # asymptote of the shoulder before floor lift
    floor=8 / 255.0,     # lifted black point, measured from references
    # Softening, fraction of long edge (Sharpness -2)
    soften=1.5e-4,
    # Grain (Strong, Large)
    grain_cell=0.0006,   # grain cell size as a fraction of the long edge
    grain_amp=0.019,     # coarse grain std in 0..1 units at mid gray
    grain_fine_amp=0.006,  # 1 px grain layer
    # Border (LOCKED): white, 2% of long edge, added after the filter
    border=0.02,
)


def tone_curve(y, p):
    """y in 0..1 (gamma-encoded gray). Returns curved y in 0..1."""
    y = np.clip(y, 0.0, 1.0) ** p["toe_gamma"]
    k, c = p["knee"], p["ceiling"]
    span = c - k
    out = np.where(y <= k, y, k + span * np.tanh((y - k) / span))
    f = p["floor"]
    return f + (1.0 - f) * out


GRAIN_SIZE_MULT = {"small": 0.5, "medium": 1.0, "large": 2.0}


def make_grain(h, w, seed, p, size="medium"):
    mult = GRAIN_SIZE_MULT[size]
    rng = np.random.default_rng(seed)
    long_edge = max(h, w)
    cell = max(1.0, p["grain_cell"] * mult * long_edge)
    # Coarse layer generated small, upsampled smoothly
    ch, cw = max(2, int(round(h / cell))), max(2, int(round(w / cell)))
    coarse = rng.standard_normal((ch, cw)).astype(np.float32)
    coarse = zoom(coarse, (h / ch, w / cw), order=3)[:h, :w]
    if coarse.shape != (h, w):  # guard against off-by-one from zoom
        pad = np.zeros((h, w), np.float32)
        pad[: coarse.shape[0], : coarse.shape[1]] = coarse
        coarse = pad
    coarse /= coarse.std() + 1e-6
    fine = rng.standard_normal((h, w)).astype(np.float32)
    fine = gaussian_filter(fine, 0.6)
    fine /= fine.std() + 1e-6
    return p["grain_amp"] * mult * coarse + p["grain_fine_amp"] * mult * fine


def to_bw(img, p):
    """WB-gain + gray-mix + tone-curve + soften. Returns a 2D float32 array,
    0..1, gamma-encoded gray."""
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    gains = np.array([p["wb_r"], p["wb_g"], p["wb_b"]], np.float32)
    mix = np.array([p["mix_r"], p["mix_g"], p["mix_b"]], np.float32) * gains
    mix /= mix.sum()
    y = rgb @ mix
    del rgb
    y = tone_curve(y, p).astype(np.float32)

    h, w = y.shape
    sigma = p["soften"] * max(h, w)
    if sigma > 0.05:
        y = gaussian_filter(y, sigma)
    return y


def _grain_weight(luma):
    return 0.45 + 0.55 * 4.0 * luma * (1.0 - luma)  # strongest in midtones


def emulate(img, seed=0, p=PARAMS, apply_bw=True, apply_grain=True, grain_size="medium"):
    if apply_bw:
        y = to_bw(img, p)
        h, w = y.shape
    else:
        rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
        h, w = rgb.shape[:2]

    if apply_grain:
        g = make_grain(h, w, seed, p, grain_size)
        if apply_bw:
            y = np.clip(y + g * _grain_weight(y), 0.0, 1.0)
        else:
            mix = np.array([p["mix_r"], p["mix_g"], p["mix_b"]], np.float32)
            mix /= mix.sum()
            luma = rgb @ mix
            weight = _grain_weight(luma)
            rgb = np.clip(rgb + g[..., None] * weight[..., None], 0.0, 1.0)

    if apply_bw:
        return Image.fromarray((y * 255.0 + 0.5).astype(np.uint8))
    return Image.fromarray((rgb * 255.0 + 0.5).astype(np.uint8))


def add_border(img, frac, value=255):
    """Uniform border, thickness = frac * long edge (resolution independent).
    Apply LAST, after the filter, so the frame stays clean and unfiltered."""
    t = round(frac * max(img.size))
    if t <= 0:
        return img
    canvas = Image.new(img.mode, (img.width + 2 * t, img.height + 2 * t), value)
    canvas.paste(img, (t, t))
    return canvas


# ------------------------------------------------------------------ layout
# Output shapes selectable from the tool. Ratios are canvas width : height.
SHAPES = {"square": (1, 1), "portrait": (4, 5), "landscape": (5, 4)}


def layout(shape, canvas_long=2400, border_frac=None):
    """Fixed-size canvas with a uniform border. The crop stage must target
    the INNER ratio (inner_w / inner_h), not the canvas ratio."""
    rw, rh = SHAPES[shape]
    border_frac = PARAMS["border"] if border_frac is None else border_frac
    long_side = canvas_long
    short_side = round(canvas_long * min(rw, rh) / max(rw, rh))
    cw, ch = (long_side, short_side) if rw >= rh else (short_side, long_side)
    t = round(border_frac * canvas_long)
    iw, ih = cw - 2 * t, ch - 2 * t
    return dict(canvas=(cw, ch), border=t, inner=(iw, ih), inner_ratio=iw / ih)


def center_crop(img, ratio):
    """PLACEHOLDER crop used only when no crop stage has run. The real crop
    (thirds / symmetry / triage) should hand this script an image already at
    the inner ratio."""
    w, h = img.size
    if w / h > ratio:
        nw = round(h * ratio)
        x = (w - nw) // 2
        return img.crop((x, 0, x + nw, h))
    nh = round(w / ratio)
    y = (h - nh) // 2
    return img.crop((0, y, w, y + nh))


def render(cropped, shape, canvas_long=2400, seed=0):
    """cropped -> resize to inner size -> filter (grain sized to the inner
    photo) -> white border -> exact canvas size."""
    lay = layout(shape, canvas_long)
    iw, ih = lay["inner"]
    if abs(cropped.width / cropped.height - lay["inner_ratio"]) > 0.005:
        raise ValueError(
            f"crop ratio {cropped.width / cropped.height:.4f} does not match "
            f"inner ratio {lay['inner_ratio']:.4f} for '{shape}'"
        )
    if cropped.width < iw or cropped.height < ih:
        import warnings
        warnings.warn(
            f"crop {cropped.size} is smaller than inner size {(iw, ih)}: the photo will be "
            f"upscaled. Use a smaller canvas or a looser crop."
        )
    img = cropped.resize((iw, ih), Image.LANCZOS)
    out = emulate(img, seed)
    t = lay["border"]
    canvas = Image.new("L", lay["canvas"], 255)
    canvas.paste(out, (t, t))
    assert canvas.size == lay["canvas"]
    return canvas


def process_file(src, dst, max_edge=None, quality=92, border=None, shape=None, canvas_long=2400):
    img = ImageOps.exif_transpose(Image.open(src))
    if shape:
        seed = int(hashlib.md5(os.path.basename(src).encode()).hexdigest()[:8], 16)
        lay = layout(shape, canvas_long)
        if abs(img.width / img.height - lay["inner_ratio"]) > 0.005:
            img = center_crop(img, lay["inner_ratio"])  # placeholder crop
        out = render(img, shape, canvas_long, seed)
        out.save(dst, quality=quality, subsampling=0, optimize=True)
        return out
    if max_edge and max(img.size) > max_edge:
        s = max_edge / max(img.size)
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    seed = int(hashlib.md5(os.path.basename(src).encode()).hexdigest()[:8], 16)
    border = PARAMS["border"] if border is None else border
    out = add_border(emulate(img, seed), border)
    out.save(dst, quality=quality, subsampling=0, optimize=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="input JPEG files")
    ap.add_argument("-o", "--outdir", default="hp5_out")
    ap.add_argument("--max-edge", type=int, default=None, help="downscale long edge before processing")
    ap.add_argument("--quality", type=int, default=92)
    ap.add_argument("--border", type=float, default=None, help="override the locked 2%% border (fraction of long edge); 0 disables. Ignored with --shape")
    ap.add_argument("--shape", choices=list(SHAPES), help="fixed canvas: square 1:1, portrait 4:5, landscape 5:4")
    ap.add_argument("--canvas-long", type=int, default=2400, help="canvas long edge in px (with --shape)")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    for src in a.inputs:
        dst = os.path.join(a.outdir, os.path.splitext(os.path.basename(src))[0] + "_hp5.jpg")
        process_file(src, dst, a.max_edge, a.quality, a.border, a.shape, a.canvas_long)
        print("wrote", dst)


if __name__ == "__main__":
    sys.exit(main())
