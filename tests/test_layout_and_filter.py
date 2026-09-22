"""Run:  python -m unittest discover -s tests -v   (from the project root)
Uses synthetic images only, so no personal photos are needed."""
import os
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import hp5_emulate as H  # noqa: E402


def synthetic(w, h, seed=0):
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 255, w, dtype=np.float32)[None, :].repeat(h, 0)
    rgb = np.stack([x, x[::-1], np.full_like(x, 128)], -1) + rng.normal(0, 3, (h, w, 3))
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


class LayoutTests(unittest.TestCase):
    def test_canvas_sizes_and_border(self):
        for long_edge in (1080, 1350, 2400, 3600, 5000):
            for shape in H.SHAPES:
                lay = H.layout(shape, long_edge)
                cw, ch = lay["canvas"]
                self.assertEqual(max(cw, ch), long_edge)
                self.assertEqual(lay["border"], round(0.02 * long_edge))
                self.assertEqual(lay["inner"], (cw - 2 * lay["border"], ch - 2 * lay["border"]))

    def test_canvas_ratios(self):
        self.assertEqual(H.layout("square", 2400)["canvas"], (2400, 2400))
        self.assertEqual(H.layout("portrait", 2400)["canvas"], (1920, 2400))
        self.assertEqual(H.layout("landscape", 2400)["canvas"], (2400, 1920))

    def test_inner_ratio_differs_from_canvas_ratio(self):
        # the crop stage must target inner_ratio, not the canvas ratio
        self.assertAlmostEqual(H.layout("portrait", 2400)["inner_ratio"], 1824 / 2304)
        self.assertNotAlmostEqual(H.layout("portrait", 2400)["inner_ratio"], 0.8, places=3)

    def test_border_size_small_matches_todays_default(self):
        # regression pin: border_size="small" must reproduce today's exact
        # output (same as calling layout() without the new parameter)
        for long_edge in (1080, 2400, 5000):
            for shape in H.SHAPES:
                default = H.layout(shape, long_edge)
                small = H.layout(shape, long_edge, border_size="small")
                self.assertEqual(small, default)

    def test_border_size_medium_and_large_are_measurably_bigger(self):
        for shape in H.SHAPES:
            small = H.layout(shape, 2400, border_size="small")["border"]
            medium = H.layout(shape, 2400, border_size="medium")["border"]
            large = H.layout(shape, 2400, border_size="large")["border"]
            self.assertEqual(medium, round(0.04 * 2400))
            self.assertEqual(large, round(0.06 * 2400))
            self.assertGreater(medium, small)
            self.assertGreater(large, medium)

    def test_explicit_border_frac_overrides_border_size(self):
        lay = H.layout("square", 2400, border_frac=0.1, border_size="large")
        self.assertEqual(lay["border"], round(0.1 * 2400))


class RenderTests(unittest.TestCase):
    def test_render_exact_canvas_and_pure_white_border(self):
        for shape in H.SHAPES:
            lay = H.layout(shape, 1350)
            iw, ih = lay["inner"]
            out = H.render(synthetic(iw * 2, ih * 2), shape, 1350, seed=1)
            self.assertEqual(out.size, lay["canvas"])
            a, t = np.asarray(out), lay["border"]
            for edge in (a[:t], a[-t:], a[:, :t], a[:, -t:]):
                self.assertEqual(int(edge.min()), 255)

    def test_render_rejects_wrong_ratio(self):
        with self.assertRaises(ValueError):
            H.render(synthetic(1000, 1000), "portrait", 1350)

    def test_upscale_warns(self):
        lay = H.layout("square", 2400)
        iw, ih = lay["inner"]
        with self.assertWarns(UserWarning):
            H.render(synthetic(iw // 2, ih // 2), "square", 2400)

    def test_deterministic_for_same_seed(self):
        img = synthetic(600, 480)
        a = np.asarray(H.emulate(img, seed=7))
        b = np.asarray(H.emulate(img, seed=7))
        self.assertTrue((a == b).all())


class ToneTests(unittest.TestCase):
    def test_curve_monotonic_with_floor_and_soft_ceiling(self):
        x = np.linspace(0, 1, 2001)
        y = H.tone_curve(x, H.PARAMS)
        self.assertTrue((np.diff(y) >= -1e-9).all())
        self.assertAlmostEqual(float(y[0]), H.PARAMS["floor"], places=6)
        self.assertLess(float(y[-1]), 0.80)  # highlights never reach white

    def test_output_highlights_stay_below_clip(self):
        out = np.asarray(H.emulate(synthetic(800, 600), seed=3)).astype(float)
        self.assertLess(np.percentile(out, 99.5), 215)
        self.assertGreater(np.percentile(out, 0.5), 2)  # blacks lifted, not crushed


class BWGrainSplitTests(unittest.TestCase):
    def test_default_kwargs_match_legacy_two_arg_call(self):
        img = synthetic(300, 200)
        legacy = np.asarray(H.emulate(img, seed=11))
        split = np.asarray(H.emulate(img, seed=11, apply_bw=True, apply_grain=True,
                                      grain_size="medium"))
        self.assertTrue((legacy == split).all())

    def test_apply_bw_false_retains_per_channel_color(self):
        out = np.asarray(H.emulate(synthetic(300, 200), seed=5, apply_bw=False,
                                    apply_grain=True)).astype(float)
        self.assertEqual(out.shape[-1], 3)
        self.assertGreater(np.abs(out[..., 0] - out[..., 1]).mean(), 2.0)

    def test_apply_bw_true_apply_grain_false_has_no_seeded_noise(self):
        flat = Image.new("RGB", (64, 64), (130, 100, 90))
        a = np.asarray(H.emulate(flat, seed=1, apply_bw=True, apply_grain=False))
        b = np.asarray(H.emulate(flat, seed=2, apply_bw=True, apply_grain=False))
        self.assertTrue((a == b).all())

    def test_grain_size_small_vs_large_differ_in_amplitude(self):
        img = synthetic(300, 200)
        baseline = np.asarray(H.emulate(img, seed=9, apply_grain=False)).astype(float)
        small = np.asarray(H.emulate(img, seed=9, grain_size="small")).astype(float)
        large = np.asarray(H.emulate(img, seed=9, grain_size="large")).astype(float)
        small_std = (small - baseline).std()
        large_std = (large - baseline).std()
        self.assertGreater(large_std, small_std * 1.5)

    def test_grain_on_color_image_is_identical_field_across_channels(self):
        # Mid-gray, low-contrast image so added grain never saturates a
        # channel (saturation clipping would legitimately make channel diffs
        # diverge even though the underlying noise field is identical).
        img = Image.new("RGB", (300, 200), (128, 120, 110))
        no_grain = np.asarray(H.emulate(img, seed=3, apply_bw=False,
                                         apply_grain=False)).astype(float)
        grained = np.asarray(H.emulate(img, seed=3, apply_bw=False,
                                        apply_grain=True)).astype(float)
        diff = grained - no_grain
        np.testing.assert_allclose(diff[..., 0], diff[..., 1], atol=1.0)
        np.testing.assert_allclose(diff[..., 0], diff[..., 2], atol=1.0)


class CliPathTests(unittest.TestCase):
    def test_process_file_shape_mode(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = os.path.join(d, "a.jpg"), os.path.join(d, "a_hp5.jpg")
            synthetic(3000, 2000).save(src, quality=95)
            H.process_file(src, dst, shape="landscape", canvas_long=1200)
            with Image.open(dst) as im:
                self.assertEqual(im.size, H.layout("landscape", 1200)["canvas"])


if __name__ == "__main__":
    unittest.main()
