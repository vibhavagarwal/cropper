#!/usr/bin/env python3
"""Rough grain level as seen at 799px wide: std of a high-pass (sigma 1.5) taken over
the flattest 20% of local-variance areas. Used to keep grain comparable to the
799px reference photos (reference values 0.27 to 3.13).  Textured scenes such as
foliage or brick read high regardless of grain, so use flat scenes (sky, water,
plain walls) when calibrating.  Usage: python tools/grain_metric.py out/*.jpg"""
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, uniform_filter


def grain_metric(path):
    im = Image.open(path).convert("L")
    s = 799 / max(im.size)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    g = np.asarray(im).astype(float)
    hp = g - gaussian_filter(g, 1.5)
    loc = np.sqrt(np.maximum(uniform_filter(g ** 2, 9) - uniform_filter(g, 9) ** 2, 0))
    return float(hp[loc < np.percentile(loc, 20)].std())


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(f, round(grain_metric(f), 2))
