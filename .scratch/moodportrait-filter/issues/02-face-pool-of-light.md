# Port the pool of light on the face, and the no-face oval

Status: resolved
Spec: ../spec.md
Blocked by: 01 only for the end-to-end test; the maths can be written and unit tested on its own

## What to build

In `src/moodportrait.py`: a `Face` dataclass (`cx, cy, w, h, roll`, all fractions of the image, roll in radians,
positive clockwise on screen), `FalloffProfile` with the shipped `REMBRANDT_PROFILE`, and `apply_falloff(graded_uint8,
face_or_None, profile)` doing `applyFaceLight` or `applyOval` from `FalloffRenderPipeline.kt`.

## Steps

1. Copy every shipped value from the spec (do not retune). Keep `foreheadStretch`, `shadowLift` and the moved-out cap
   as parameters defaulting to the shipped "off" values (1.0, 0.0, 0.8/1.5/0.45).
2. Vectorise with numpy: per-pixel distance in the face's tilted axes, Gaussian tail, the monotonic ceiling
   `x / sqrt(1 + (x/c)^2)` faded in by smoothstep, `blendToTarget` with `shadowWarmth`. Note the reference uses
   **pixel centres** `(x+0.5)/W`, **truncation** for the face-luma 8x8 sample grid (`toInt`), and clamps/rounds with
   `+0.5` then `toInt`; reproduce these so output can match within rounding.
3. Face luma is measured on the **graded** image (the one passed in), the face itself comes from the source image.
4. No face: the frame-centred oval with the fallback values in the spec.
5. Tests (synthetic): fully lit centre unchanged-ish, corners go to the ground colour, output never brighter than
   the pre-ceiling input outside the face box, monotonic (a brighter pixel never ends up darker than a dimmer one at
   the same position), options-off output equals shipped output, no-face path used when `face is None`.

## Acceptance

- [ ] Shipped values match the spec exactly (a test asserts the constants)
- [ ] The three off-by-default options are present and tested on, but off in the default profile
- [ ] No-face fallback matches the reference oval

## Comments

Implemented in `src/moodportrait.py` (`Face`, `FalloffProfile`, `apply_falloff`, `face_in_crop`). Shipped values asserted by a test; the three tried-and-off options are parameters defaulting off. Output vs FujiVibe's render with the same face file: 1.7-1.9 mean abs diff (their JPEG has grain, ours none). 0.4 s at 2300x1840.
