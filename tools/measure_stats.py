#!/usr/bin/env python3
"""Print luma percentiles for images, to compare filter output against
docs/reference_stats.json.  Usage: python tools/measure_stats.py out/*.jpg"""
import sys
import numpy as np
from PIL import Image

PCTS = [0.5, 2, 10, 25, 50, 75, 90, 98, 99.5]


def stats(path):
    g = np.asarray(Image.open(path).convert("L")).astype(float)
    return dict(zip(["p%s" % p for p in PCTS], np.round(np.percentile(g, PCTS)).astype(int).tolist()),
                std=round(float(g.std())), max=int(g.max()))


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(f, stats(f))
