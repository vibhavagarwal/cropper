# Haar cascade face detector false-positives heavily on repetitive/textured backgrounds

Status: requested 2026-09-21, not scoped

## Observed

User's Details dialog screenshot for a shoe-display photo (pegboard wall, sneakers, shadows,
repetitive hole/edge patterns) shows **"Faces detected: 77"**, with red detection boxes
scattered across shoe outlines, pegboard holes, and shadow edges - no actual faces present in
the photo at all. This also directly poisons triage: the same photo's escalation reasons show
`"multiple faces with no clear primary subject"`, so this false-positive flood isn't just a
cosmetic overlay problem, it's actively driving (wrong) escalation decisions.

## Likely root cause (checked, not fixed)

`src/detection.py:48-52`, `detect_faces()`:

```python
def detect_faces(gray: np.ndarray) -> list:
    boxes = _face_cascade().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
    )
    return [FaceBox(int(x), int(y), int(w), int(h)) for (x, y, w, h) in boxes]
```

Uses OpenCV's stock `haarcascade_frontalface_default.xml` Haar cascade. Haar cascades are
well-known to false-positive on repetitive, high-contrast textured regions (grids, pegboard
holes, fabric weave, foliage) - exactly the kind of image shown. `minNeighbors=5` is on the
lower end of typical tuning ranges (OpenCV's own docs/examples often go higher, e.g. 6-10, to
suppress spurious clusters); `scaleFactor=1.1` and `minSize=(40, 40)` are otherwise fairly
standard defaults, not obviously the problem by themselves.

## Not yet investigated / open questions for whoever scopes this

- Has this been reproduced on other non-portrait photos (repetitive patterns, product shots,
  architecture), or is this the only confirmed case so far? Worth a quick sweep of a few more
  "busy background, no faces" test photos before concluding it's systemic rather than this one
  image.
- Possible directions, **none decided**: (a) retune `minNeighbors`/`scaleFactor`/`minSize`
  against a labeled batch (same "don't eyeball it" guidance already called out for
  `src/triage.py`'s `THRESHOLDS` and `src/detection.py`'s own module docstring); (b) add a
  post-filter (e.g. cap max face count, or discard detections in low-variance/high-repetition
  regions); (c) swap the Haar cascade for a stronger detector (DNN-based face detector already
  bundled with OpenCV, e.g. `cv2.FaceDetectorYN`) - a bigger change, not a tuning tweak.
- This is a detection-quality issue, not a triage-threshold issue - distinct from
  `.scratch/triage-and-border-tuning/issues/01-remove-saliency-edge-touch-from-triage.md`, which
  addressed a different false-positive source (the saliency edge-touch check). That ticket does
  NOT fix this; the "multiple faces" triage condition (`src/triage.py`) is downstream of this bug
  and inherits it directly.

## Comments
