"""Local-only parity check (not run in CI, no photos committed): render FujiVibe's test photos through Cropper's
MoodPortrait (grade + pool of light, no grain) and compare with FujiVibe's own renders.

Usage: python -I tools/moodportrait_parity.py <fujivibe .scratch/rembrandt dir> <out dir>
Pairs are by name: cafe/hat/sky/puppets -> the original JPEG each was made from."""
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

import face_blaze as fb  # noqa: E402
import moodportrait as mp  # noqa: E402

PAIRS = {"cafe": "4266DB12-4BAD-48BD-ACCD-EEE560B9F228.JPG", "hat": "DSCF1170.JPG",
         "sky": "DSCF0027.JPG", "puppets": "PXL_20240801_121015330.jpg"}


def stats(a, b):
    d = np.abs(a.astype(int) - b.astype(int))
    return f"mean {d.mean():.2f}  p99 {np.percentile(d, 99):.0f}  max {d.max()}  >8: {100 * (d > 8).mean():.2f}%"


def main(ref_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, src in PAIRS.items():
        ref = Image.open(os.path.join(ref_dir, "rendered", "face-pool", f"{name}-rembrandt.jpg")).convert("RGB")
        full = ImageOps.exif_transpose(Image.open(os.path.join(ref_dir, src))).convert("RGB")
        img = np.asarray(full.resize(ref.size, Image.LANCZOS))  # FujiVibe rendered a pre-shrunk copy
        refa = np.asarray(ref)
        cx, cy, w, h, roll = (float(x) for x in open(os.path.join(ref_dir, "faces", f"{name}.face.txt")).read().split())
        graded = mp.apply_grade(img)
        same_face = mp.apply_falloff(graded, mp.Face(cx, cy, w, h, roll))
        t = time.time()
        found = fb.find_face(np.asarray(full))
        t_detect = time.time() - t
        own = mp.apply_falloff(graded, mp.Face(found.cx, found.cy, found.w, found.h, found.roll)) if found else None
        print(f"{name}: {ref.size}")
        print("  grade only vs ref     ", stats(graded, refa), "(ref also has pool + grain)")
        print("  FujiVibe face vs ref  ", stats(same_face, refa), "(ref has grain, ours none)")
        if found:
            print("  Cropper BlazeFace     ", stats(own, refa), f" detect {t_detect:.2f}s on {full.size}")
            print(f"    face ref=({cx:.3f},{cy:.3f},{w:.3f},{h:.3f},{math.degrees(roll):.1f}deg) "
                  f"ours=({found.cx:.3f},{found.cy:.3f},{found.w:.3f},{found.h:.3f},{math.degrees(found.roll):.1f}deg)")
        th = 600 / ref.size[1]
        tw = int(ref.size[0] * th)
        panels = [img, refa, same_face] + ([own] if own is not None else [])
        sheet = Image.new("RGB", (tw * len(panels), 600))
        for i, p in enumerate(panels):
            sheet.paste(Image.fromarray(np.asarray(p)).resize((tw, 600), Image.LANCZOS), (i * tw, 0))
        sheet.save(os.path.join(out_dir, f"{name}-parity.jpg"), quality=90)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
