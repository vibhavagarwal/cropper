"""Run:  python -m unittest tests.test_moodportrait -v   (from the project root)
Synthetic images only, so no personal photos are needed."""
import math
import os
import sys
import unittest
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import face_blaze as fb  # noqa: E402
import moodportrait as mp  # noqa: E402


# --- test oracle: FujiVibe's RembrandtCorrection.kt, used only to check the baked .cube -------------------------
def _tone(x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    d = x ** 1.45
    return d ** 1.35 / (d ** 1.35 + (1 - d) ** 1.35)


def _smooth(t):
    t = min(1, max(0, t))
    return t * t * (3 - 2 * t)


def _sat(h):
    if h <= 65:
        return 0.92
    if h < 95:
        return 0.92 + (0.30 - 0.92) * _smooth((h - 65) / 30)
    if h <= 255:
        return 0.30
    if h < 295:
        return 0.30 + (0.55 - 0.30) * _smooth((h - 255) / 40)
    if h < 345:
        return 0.55 + (0.92 - 0.55) * _smooth((h - 295) / 50)
    return 0.92


def oracle(r, g, b):
    r, g, b = min(r * 1.04, 1), g, min(b * 0.93, 1)
    r, g, b = _tone(r), _tone(g), _tone(b)
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d >= 1e-6:
        if mx == r:
            hue = ((g - b) / d) % 6
        elif mx == g:
            hue = (b - r) / d + 2
        else:
            hue = (r - g) / d + 4
        f = _sat(hue * 60)
        r, g, b = mx - (mx - r) * f, mx - (mx - g) * f, mx - (mx - b) * f
    l = min(1, max(0, 0.2126 * r + 0.7152 * g + 0.0722 * b))
    sw, hw = (1 - l) ** 2 * 0.30, l * l
    out = []
    for v, s, c in ((r, 0.26, 1.0), (g, 0.15, 0.975), (b, 0.07, 0.89)):
        v = v + (s - v) * sw
        out.append(min(1, max(0, v * (1 + (c - 1) * hw))))
    return out


class GradeTests(unittest.TestCase):
    def test_black_and_white_corners(self):
        px = np.array([[[0, 0, 0], [255, 255, 255]]], np.uint8)
        out = mp.apply_grade(px)
        self.assertEqual(out[0, 0].tolist(), [round(0.078 * 255), round(0.045 * 255), round(0.021 * 255)])
        want = [round(v * 255) for v in oracle(1, 1, 1)]  # white stays near white, tinted cream
        self.assertLessEqual(max(abs(a - b) for a, b in zip(out[0, 1].tolist(), want)), 2)

    def test_matches_correction_oracle(self):
        rng = np.random.default_rng(1)
        px = rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)
        out = mp.apply_grade(px).astype(int)
        want = np.array([[oracle(*(p / 255.0)) for p in row] for row in px]) * 255
        # the .cube is 32 points, so trilinear interpolation differs from the exact curve by a few steps
        self.assertLess(np.abs(out - want).max(), 6)
        self.assertLess(np.abs(out - want).mean(), 1.0)

    def test_does_not_mutate_input_and_keeps_shape(self):
        px = np.random.default_rng(2).integers(0, 256, (300, 17, 3), dtype=np.uint8)
        keep = px.copy()
        out = mp.apply_grade(px)
        self.assertEqual(out.shape, px.shape)
        self.assertEqual(out.dtype, np.uint8)
        self.assertTrue((px == keep).all())


class FalloffTests(unittest.TestCase):
    def setUp(self):
        self.img = np.full((200, 160, 3), 150, np.uint8)
        self.face = mp.Face(0.5, 0.45, 0.30, 0.25, 0.1)

    def test_shipped_values_exact(self):
        p = mp.REMBRANDT_PROFILE
        self.assertEqual((p.pool_inner, p.pool_sigma, p.pool_min_half_size, p.face_strength),
                         (0.9, 1.1, 0.20, 0.94))
        self.assertEqual((p.ceiling_ratio, p.ceiling_min, p.ceiling_max, p.ceiling_from, p.ceiling_over),
                         (1.5, 0.45, 0.70, 0.8, 0.5))
        self.assertEqual((p.shadow_warmth, p.ground), (0.16, (0.06, 0.035, 0.02)))
        self.assertEqual((p.center_x, p.center_y, p.radius_x, p.inner_radius, p.outer_radius, p.strength),
                         (0.5, 0.42, 0.58, 0.35, 1.0, 0.92))

    def test_tried_options_are_off_by_default(self):
        p = mp.REMBRANDT_PROFILE
        self.assertEqual((p.forehead_stretch, p.shadow_lift), (1.0, 0.0))
        on = mp.FalloffProfile(forehead_stretch=1.35, shadow_lift=0.08)
        self.assertFalse((mp.apply_falloff(self.img, self.face, on) == mp.apply_falloff(self.img, self.face)).all())

    def test_face_centre_bright_corners_dark(self):
        out = mp.apply_falloff(self.img, self.face)
        centre = out[90, 80].astype(int)
        corner = out[0, 0].astype(int)
        self.assertGreater(centre.sum(), corner.sum() * 3)
        ground = np.array(mp.REMBRANDT_PROFILE.ground) * 255
        self.assertLess(np.abs(corner - ground).max(), 25)

    def test_brighter_pixel_never_renders_darker(self):
        # the ceiling is strictly increasing, so a brighter wall can never come out dimmer than a dimmer one
        dark = np.full((200, 160, 3), 60, np.uint8)
        light = np.full((200, 160, 3), 220, np.uint8)
        a = mp.apply_falloff(dark, self.face).astype(int)
        b = mp.apply_falloff(light, self.face).astype(int)
        self.assertTrue((b >= a).all())

    def test_no_face_uses_oval(self):
        out = mp.apply_falloff(self.img, None)
        self.assertTrue((out[84, 80] == self.img[84, 80]).all())          # clear centre untouched
        self.assertLess(int(out[0, 0].sum()), int(self.img[0, 0].sum()))  # corner darkened
        self.assertFalse((out == mp.apply_falloff(self.img, self.face)).all())

    def test_face_in_crop_remap(self):
        crop = SimpleNamespace(x0=0.25, y0=0.0, x1=0.75, y1=0.5)
        f = mp.face_in_crop(mp.Face(0.5, 0.25, 0.2, 0.1, 0.3), crop)
        self.assertAlmostEqual(f.cx, 0.5)
        self.assertAlmostEqual(f.cy, 0.5)
        self.assertAlmostEqual(f.w, 0.4)
        self.assertAlmostEqual(f.h, 0.2)
        self.assertEqual(f.roll, 0.3)
        edge = mp.face_in_crop(mp.Face(0.25, 0.1, 0.2, 0.1), crop)  # face centred on the crop's left edge
        self.assertAlmostEqual(edge.cx, 0.0)


class FaceFinderTests(unittest.TestCase):
    def test_blank_image_is_no_face(self):
        self.assertIsNone(fb.find_face(np.full((300, 400, 3), 128, np.uint8)))

    def test_garbage_input_never_raises(self):
        self.assertIsNone(fb.find_face(np.zeros((0, 0, 3), np.uint8)))

    def test_anchor_count(self):
        self.assertEqual(fb._anchors().shape, (896, 2))

    def test_large_image_is_downscaled_for_detection(self):
        # a 24 MP blank frame must still return quickly with no face rather than failing
        self.assertIsNone(fb.find_face(np.full((6000, 4000, 3), 90, np.uint8)))


if __name__ == "__main__":
    unittest.main()


class MultiFaceTests(unittest.TestCase):
    def setUp(self):
        self.img = np.full((200, 300, 3), 150, np.uint8)

    def test_select_faces_keeps_up_to_two_large(self):
        big, mid, small, third = (mp.Face(.3, .5, .3, .3), mp.Face(.7, .5, .25, .25),
                                  mp.Face(.5, .2, .05, .05), mp.Face(.1, .1, .24, .24))
        self.assertEqual(mp.select_faces([small, big, mid]), [big, mid])      # small face not large enough
        self.assertEqual(mp.select_faces([big, mid, third]), [big, mid])      # at most two
        self.assertEqual(mp.select_faces([big, small]), [big])
        self.assertEqual(mp.select_faces([]), [])

    def test_single_face_in_list_equals_single_face(self):
        f = mp.Face(.5, .45, .3, .25, .1)
        self.assertTrue((mp.apply_falloff(self.img, f) == mp.apply_falloff(self.img, [f])).all())

    def test_small_extra_face_changes_nothing(self):
        f = mp.Face(.5, .45, .3, .25, .1)
        tiny = mp.Face(.9, .9, .03, .03)
        self.assertTrue((mp.apply_falloff(self.img, f) == mp.apply_falloff(self.img, [f, tiny])).all())

    def test_second_large_face_is_lit(self):
        left, right = mp.Face(.2, .5, .22, .3), mp.Face(.8, .5, .22, .3)
        one = mp.apply_falloff(self.img, [left]).astype(int)
        two = mp.apply_falloff(self.img, [left, right]).astype(int)
        self.assertGreater(two[100, 240].sum(), one[100, 240].sum() * 2)   # right face brightened by its own pool
        self.assertTrue((two[100, 60] == one[100, 60]).all() or abs(two[100, 60] - one[100, 60]).max() <= 40)


class PipelineLookTests(unittest.TestCase):
    def test_moodportrait_render_is_colour_with_white_border_and_no_face_oval(self):
        import tempfile
        from PIL import Image
        import pipeline as P
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.jpg")
            Image.fromarray(np.random.default_rng(3).integers(60, 200, (300, 400, 3), dtype=np.uint8)).save(path)
            job = P.process_photo(path, "square", 600, False, False, "medium", "small", moodportrait=True)
            self.assertIsNone(job.error)
            self.assertEqual(job.rendered.mode, "RGB")
            self.assertEqual(job.rendered.size, (600, 600))
            self.assertEqual(job.rendered.getpixel((0, 0)), (255, 255, 255))   # border stays clean
            self.assertEqual(job.look_faces, [])                              # noise has no face: oval fallback
            plain = P.process_photo(path, "square", 600, False, False, "medium", "small")
            self.assertNotEqual(job.rendered.getpixel((20, 20)), plain.rendered.getpixel((20, 20)))

    def test_old_settings_file_derives_look(self):
        from settings import AppSettings
        self.assertEqual(AppSettings(apply_bw=False).look, "none")
        self.assertEqual(AppSettings(apply_bw=True).look, "bw")
        self.assertEqual(AppSettings(look="moodportrait").look, "moodportrait")
