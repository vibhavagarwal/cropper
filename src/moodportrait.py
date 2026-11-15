"""MoodPortrait: a warm, low-key portrait look, ported from the user's FujiVibe project (built there as "Rembrandt").

Stages, in order, on an RGB uint8 image (each stage rounds to 8 bits, as the reference does):
  1. apply_grade:   the baked 32-point LUT `luts/rembrandt_srgb.cube` (sRGB in/out), trilinear, red-fastest order.
  2. apply_falloff: a pool of light on the face with everything else sinking into dark umber; a frame-centred oval
                    when no face is given.
Grain is NOT part of this module: Cropper's own grain controls are used (the canvas grain in FujiVibe is not ported).

Maths and every constant are copied from FujiVibe's FalloffRenderPipeline.kt (the shipped REMBRANDT_PROFILE). The
three options FujiVibe tried and switched off are kept as parameters and default to off: do not enable them (the user
preferred the look without them), and do not "fix" the known flaws (halo, grey forehead patch, dark eyes, dulled
bright clothes, largest face only). See .scratch/moodportrait-filter/spec.md.
"""
import math
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

_LUT_PATH = os.path.join(os.path.dirname(__file__), "luts", "rembrandt_srgb.cube")
_LUT = None
_ROWS = 256  # row chunk size: keeps peak memory low and gives the thread pool work to share


@dataclass(frozen=True)
class Face:
    """Fractions of the image (so it applies at any resolution). roll: radians, positive clockwise on screen."""
    cx: float
    cy: float
    w: float
    h: float
    roll: float = 0.0


@dataclass(frozen=True)
class FalloffProfile:
    # no-face oval
    center_x: float = 0.5
    center_y: float = 0.42
    radius_x: float = 0.58
    radius_y: float = 0.58
    inner_radius: float = 0.35
    outer_radius: float = 1.0
    strength: float = 0.92
    # face light: the shipped values
    pool_inner: float = 0.9
    pool_sigma: float = 1.1
    pool_min_half_size: float = 0.20
    face_strength: float = 0.94
    ceiling_ratio: float = 1.5
    ceiling_min: float = 0.45
    ceiling_max: float = 0.70
    ceiling_from: float = 0.8
    ceiling_over: float = 0.5
    # tried by the user and switched off (shipped values here): keep off
    forehead_stretch: float = 1.0
    shadow_lift: float = 0.0
    shadow_warmth: float = 0.16
    ground: tuple = (0.06, 0.035, 0.02)


REMBRANDT_PROFILE = FalloffProfile()


# ----------------------------------------------------------------------------------------------------- grade
def _lut() -> np.ndarray:
    """(size, size, size, 3) float32 indexed [b, g, r]: .cube data is red-fastest, then green, then blue."""
    global _LUT
    if _LUT is None:
        size = None
        rows = []
        with open(_LUT_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("LUT_3D_SIZE"):
                    size = int(line.split()[1])
                elif line[0] in "-0123456789.":
                    rows.append(line.split())
        _LUT = np.asarray(rows, np.float32).reshape(size, size, size, 3)
    return _LUT


def _grade_rows(rgb: np.ndarray, lut: np.ndarray) -> np.ndarray:
    size = lut.shape[0]
    h, w, _ = rgb.shape
    f = rgb.reshape(-1, 3).astype(np.float32) * ((size - 1) / 255.0)
    i = np.minimum(f.astype(np.int32), size - 2)
    t = f - i
    r0, g0, b0 = i[:, 0], i[:, 1], i[:, 2]
    rt, gt, bt = t[:, 0], t[:, 1], t[:, 2]
    out = np.zeros(f.shape, np.float32)
    for db in (0, 1):
        for dg in (0, 1):
            for dr in (0, 1):
                wgt = ((rt if dr else 1 - rt) * (gt if dg else 1 - gt) * (bt if db else 1 - bt))[:, None]
                out += lut[b0 + db, g0 + dg, r0 + dr] * wgt
    return (np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).reshape(h, w, 3)


def apply_grade(rgb: np.ndarray) -> np.ndarray:
    """Apply the MoodPortrait LUT to an (H, W, 3) uint8 array. Returns a new uint8 array."""
    lut = _lut()
    out = np.empty_like(rgb)
    spans = [(y, min(y + _ROWS, rgb.shape[0])) for y in range(0, rgb.shape[0], _ROWS)]

    def work(span):
        y0, y1 = span
        out[y0:y1] = _grade_rows(rgb[y0:y1], lut)

    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as pool:
        list(pool.map(work, spans))
    return out


# --------------------------------------------------------------------------------------------------- falloff
def _smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def _luma(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]) / 255.0


def _blend_to_target(px, ground, weight, scale, warmth):
    """px float32 (n,3) 0..255; weight (n,1); scale (n,1). Mirrors FalloffRenderPipeline.blendToTarget."""
    tint = warmth * weight
    mult = np.concatenate([1.0 + tint, np.ones_like(tint), 1.0 - 2.0 * tint], axis=-1)
    out = px * scale * mult * (1.0 - weight) + np.asarray(ground, np.float32) * 255.0 * weight + 0.5
    return np.clip(out, 0, 255).astype(np.uint8)


def _face_luma(rgb: np.ndarray, face: Face) -> float:
    """Mean brightness (0..1) over an 8x8 grid across the middle of the face box (truncating, as the reference)."""
    h, w, _ = rgb.shape
    k = (np.arange(8) - 3.5) / 3.5
    xs = np.clip(((face.cx + k * face.w * 0.25) * w).astype(np.int64), 0, w - 1)
    ys = np.clip(((face.cy + k * face.h * 0.25) * h).astype(np.int64), 0, h - 1)
    return float(_luma(rgb[np.ix_(ys, xs)].astype(np.float32)).mean())


def select_faces(faces) -> list:
    """The faces to light: up to two 'large' ones. Large = area at least half the largest face's. Largest first.
    With one qualifying face the look is exactly FujiVibe's single-face look."""
    faces = sorted((f for f in (faces or []) if f is not None), key=lambda f: f.w * f.h, reverse=True)
    if not faces:
        return []
    return [f for f in faces[:2] if f.w * f.h >= 0.5 * faces[0].w * faces[0].h]


def apply_falloff(rgb: np.ndarray, face=None, profile: FalloffProfile = REMBRANDT_PROFILE) -> np.ndarray:
    """Sink the (already graded) image into the dark ground: a pool of light on `face` (a Face, or a list of up to two
    Faces, each getting its own pool), or the frame-centred oval when there is no face."""
    h, w, _ = rgb.shape
    out = np.empty_like(rgb)
    faces = [face] if isinstance(face, Face) else select_faces(face)
    if not faces:
        def band(y0, y1):
            u = ((np.arange(w) + 0.5) / w)[None, :]
            v = ((np.arange(y0, y1) + 0.5) / h)[:, None]
            d2 = ((u - profile.center_x) / profile.radius_x) ** 2 + ((v - profile.center_y) / profile.radius_y) ** 2
            i2, o2 = profile.inner_radius ** 2, profile.outer_radius ** 2
            edge = np.where(d2 <= i2, 0.0, _smoothstep(np.clip((d2 - i2) / (o2 - i2), 0, 1)))
            wt = (edge * profile.strength).astype(np.float32)[..., None]
            px = rgb[y0:y1].astype(np.float32)
            res = _blend_to_target(px, profile.ground, wt, 1.0, 0.0)
            out[y0:y1] = np.where(wt <= 0, rgb[y0:y1], res)
    else:
        geo = []
        for f in faces:
            half_w = max(f.w * w / 2.0, 1.0)
            half_h = max(f.h * h / 2.0, 1.0)
            pool_scale = max(1.0, profile.pool_min_half_size * w / max(half_w, half_h))
            geo.append((f, half_w * pool_scale, half_h * pool_scale, pool_scale, math.cos(f.roll), math.sin(f.roll)))
        # one face: its own brightness; two: the mean of theirs
        face_luma = sum(_face_luma(rgb, f) for f in faces) / len(faces)
        ceiling = float(np.clip(face_luma * profile.ceiling_ratio, profile.ceiling_min, profile.ceiling_max))

        def band(y0, y1):
            u = ((np.arange(w) + 0.5) / w)[None, :]
            v = ((np.arange(y0, y1) + 0.5) / h)[:, None]
            pool = None       # strongest pool among the faces
            near = None       # distance to the nearest face (for the brightness cap)
            box_near = None   # same, in real face-box units (for the shadow lift)
            for f, half_w, half_h, pool_scale, cos_r, sin_r in geo:
                px, py = (u - f.cx) * w, (v - f.cy) * h
                fx = (px * cos_r + py * sin_r) / half_w
                fy = (-px * sin_r + py * cos_r) / half_h
                fy_s = np.where(fy < 0, fy / profile.forehead_stretch, fy)
                dist = np.sqrt(fx * fx + fy_s * fy_s).astype(np.float32)
                beyond = np.maximum(dist - profile.pool_inner, 0.0) / profile.pool_sigma
                this_pool = np.exp(-0.5 * beyond * beyond)
                this_near = dist * pool_scale
                this_box = np.sqrt(fx * fx + fy * fy).astype(np.float32) * pool_scale
                pool = this_pool if pool is None else np.maximum(pool, this_pool)
                near = this_near if near is None else np.minimum(near, this_near)
                box_near = this_box if box_near is None else np.minimum(box_near, this_box)
            wt = (profile.face_strength * (1.0 - pool))[..., None].astype(np.float32)

            src = rgb[y0:y1].astype(np.float32)
            luma = _luma(src)
            ratio = 1.0 / np.sqrt(1.0 + (luma / ceiling) ** 2)
            ramp = _smoothstep(np.clip((near - profile.ceiling_from) / profile.ceiling_over, 0, 1))
            scale = (1.0 + (ratio - 1.0) * ramp)[..., None].astype(np.float32)

            if profile.shadow_lift > 0.0:
                dark = np.maximum(1.0 - 2.0 * luma, 0.0)
                in_face = 1.0 - _smoothstep(np.clip((box_near - 0.8) / 0.4, 0, 1))
                lift = (profile.shadow_lift * dark * dark * in_face)[..., None]
                src = np.minimum(src + lift * 255.0 * np.array([1.0, 0.82, 0.62], np.float32), 255.0)
            out[y0:y1] = _blend_to_target(src, profile.ground, wt, scale, profile.shadow_warmth)

    spans = [(y, min(y + _ROWS, h)) for y in range(0, h, _ROWS)]
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as pool:
        list(pool.map(lambda s: band(*s), spans))
    return out


# ----------------------------------------------------------------------------------------------------- whole
def render_look(rgb: np.ndarray, face=None, profile: FalloffProfile = REMBRANDT_PROFILE) -> np.ndarray:
    """Grade then pool of light. `face` (a Face, a list of Faces, or None) is in the coordinates of `rgb` (see faces_in_crop)."""
    return apply_falloff(apply_grade(rgb), face, profile)


def faces_in_crop(faces, crop) -> list:
    """face_in_crop for a list of faces (anything with cx, cy, w, h, roll, e.g. face_blaze.BlazeFace)."""
    return [face_in_crop(Face(f.cx, f.cy, f.w, f.h, f.roll), crop) for f in faces or []]


def face_in_crop(face: Face, crop) -> Face:
    """Remap a face given as fractions of the original into fractions of the crop. `crop` has x0, y0, x1, y1 as
    fractions of the original (Cropper's CropBox). The face may extend past the crop; that is fine."""
    cw, ch = crop.x1 - crop.x0, crop.y1 - crop.y0
    return Face((face.cx - crop.x0) / cw, (face.cy - crop.y0) / ch, face.w / cw, face.h / ch, face.roll)
