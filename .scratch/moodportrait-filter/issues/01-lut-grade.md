# Port the colour grade: load the .cube and apply it fast

Status: resolved
Spec: ../spec.md

## What to build

`src/moodportrait.py` (new) with the grade stage: parse `Rembrandt sRGB.cube`, apply it with trilinear interpolation
to a uint8 RGB array, return uint8 (round to nearest, as the reference does).

## Steps

1. Copy `derived-luts/Rembrandt sRGB.cube` from FujiVibe into `src/luts/` (it is a 32-point LUT, ~32k lines; not a
   personal photo, fine to commit). Bundle it in `cropper.spec` `datas` the way the YuNet model is.
2. Parser: `LUT_3D_SIZE 32`, then `size^3` lines, **red fastest, then green, then blue**.
3. Apply: `idx = rgb/255*(size-1)`, floor clamped to `size-2`, 8 neighbour gather, trilinear (match
   `Cube3DLut.sampleInto`). Process in row chunks (and a small thread pool if it helps) so peak memory stays low and it
   is fast; the naive whole-image version measured 3.5 s at 2300x1840 and 16 s at 24 MP.
4. Test oracle: a small Python port of `RembrandtCorrection.correct` used **only in tests** to check the `.cube`
   (corners, mid-grey, a skin-tone sample) to within one 8-bit step.

## Acceptance

- [ ] LUT output on a synthetic gradient matches the oracle within 1/255 per channel
- [ ] Output dtype/shape correct, no change to the input array
- [ ] 2300x1840 in under 3 s on the user's laptop (report the number)
- [ ] Synthetic images only in tests (no personal photos)

## Comments

Implemented in `src/moodportrait.py` (`apply_grade`), LUT in `src/luts/rembrandt_srgb.cube`, bundled in `cropper.spec`. Test oracle in `tests/test_moodportrait.py`: max error 6/255 vs the exact curve (inherent to a 32-point LUT; the reference interpolates the same way), mean under 1. Speed: 1.1 s at 2300x1840 (target was under 3 s), 5.9 s at 24 MP.
