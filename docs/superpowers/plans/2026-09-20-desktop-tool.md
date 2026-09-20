# Cropper Desktop Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Cropper desktop tool — a PySide6 GUI wrapping a photo-processing pipeline (EXIF correction, face/saliency/symmetry detection, triage, formula crop, provider-agnostic AI-escalated crop, HP5 film filter, fixed-canvas layout) with an explicit review-and-save workflow and cost-gated paid AI calls.

**Architecture:** Two phases. Phase 1 builds a pure-Python "engine" (`src/`) with no GUI dependency — detection, triage, crop math, cost estimation, the provider-agnostic AI interface, settings, and decision logging — each piece unit-tested with `unittest`, reusing the existing `src/hp5_emulate.py` filter/layout code unchanged. Phase 2 builds the PySide6 GUI (`gui/`) on top of the engine: input panel, background workers, review gallery, manual crop editor, escalation flow, cost panel. A hard checkpoint (Task 11) requires the full engine test suite green before any GUI code is written.

**Tech Stack:** Python 3.14.7, PySide6, numpy, scipy, Pillow, opencv-contrib-python, openai, keyring. All versions pinned and verified together (see Global Constraints).

**Spec:** [.scratch/desktop-tool/spec.md](../../../.scratch/desktop-tool/spec.md) — this plan implements every decision in that spec. The spec in turn treats `docs/pipeline-brief.md` (Task 1 copies it in) as the settled source of pipeline requirements (locked pipeline order, output layout, cost analysis).

## Global Constraints

- Python 3.14.7 (already installed on the target machine; do not require a different Python).
- Pinned dependency versions (verified together against the existing test suite — do not substitute):
  `PySide6==6.11.2`, `numpy==2.5.3`, `scipy==1.18.1`, `Pillow==12.3.0`, `opencv-contrib-python==4.11.0.86`, `openai==3.16.2`, `keyring==25.7.0`.
- **Use `opencv-contrib-python`, never `opencv-python`.** Verified during planning: `opencv-python` 5.0.0 ships no bundled Haar-cascade XML files and has no `cv2.saliency` module at all. `opencv-contrib-python==4.11.0.86` has both (`cv2.data.haarcascades` contains 17 XML files including `haarcascade_frontalface_default.xml`; `cv2.saliency.StaticSaliencySpectralResidual_create()` works). Never `pip install` both in the same environment — they conflict on the same `cv2` import namespace.
- Existing `tests/test_layout_and_filter.py` and `src/hp5_emulate.py` must keep passing/working **unmodified** throughout every task.
- Border is a **locked** pipeline decision: white, uniform, 2% of canvas long edge, always applied after the filter. Never expose it as a setting anywhere in the GUI.
- Exactly one output shape applies per processing run (no per-photo shape mixing in a single run).
- Only the landscape HP5 filter exists; it applies to all photos for now (portrait filter is explicitly deferred — do not design or stub it).
- Nothing ever writes to the output folder automatically. Every write to disk happens only from the explicit Save action.
- Any call that spends money (AI escalation) is never automatic across a batch — always an explicit user action, and always preceded by a worst-case cost estimate (assume the stronger/pricier tier for every flagged photo).
- Escalation tier selection (cheap first, escalate to strong only on low confidence) is fully automatic — no manual override setting.
- Triage thresholds live in code (`src/triage.py`, a `THRESHOLDS` dict) — no in-app settings UI for them, matching the existing `PARAMS`-dict convention in `src/hp5_emulate.py`.
- First (and only, for this plan) AI provider implementation: OpenAI. The user has OpenAI API billing already set up; do not implement Anthropic or other providers in this plan — only the interface that would let one be added later.
- App is local-only: run from source (`python gui/main.py`), no packaging/installer step in this plan.

---

## File Structure

```
Cropper/
├── docs/
│   ├── pipeline-brief.md          # NEW (Task 1): the starter zip's own CLAUDE.md, renamed to
│   │                               #   avoid colliding with this repo's existing CLAUDE.md
│   ├── filter_hp5_notes.md        # NEW (Task 1): copied from the starter zip, unchanged
│   ├── reference_stats.json       # NEW (Task 1): copied from the starter zip, unchanged
│   └── agents/                    # existing, untouched
├── requirements.txt                # NEW (Task 1): pinned dependency list
├── src/
│   ├── hp5_emulate.py             # NEW (Task 1): copied from the starter zip, unchanged
│   ├── detection.py                # NEW (Task 2): face/saliency/symmetry detection
│   ├── triage.py                   # NEW (Task 3): escalation decision + thresholds
│   ├── crop.py                     # NEW (Task 4): formula crop (rule of thirds / symmetry)
│   ├── providers/
│   │   ├── __init__.py             # NEW (Task 5)
│   │   ├── base.py                 # NEW (Task 5): CropProvider interface, CropDecision
│   │   └── openai_provider.py      # NEW (Task 6): OpenAI implementation
│   ├── cost.py                      # NEW (Task 7): worst-case cost estimation
│   ├── decision_log.py              # NEW (Task 8): per-photo decision log, running cost
│   ├── settings.py                  # NEW (Task 9): persisted app settings
│   └── pipeline.py                  # NEW (Task 10): orchestrates the above into PhotoJob
├── gui/
│   ├── __init__.py                  # NEW (Task 12)
│   ├── main.py                       # NEW (Task 12): entrypoint
│   ├── main_window.py                # NEW (Task 12, wired in Task 21): MainWindow
│   ├── input_panel.py                 # NEW (Task 13): folder picker, drag-drop, controls
│   ├── workers.py                     # NEW (Task 14): QThread background workers
│   ├── review_gallery.py              # NEW (Task 15): thumbnail grid, keep/discard
│   ├── detail_view_dialog.py          # NEW (Task 16): detection overlay + confidence/tier
│   ├── crop_editor_dialog.py          # NEW (Task 17): interactive ratio-locked crop box
│   ├── cost_panel.py                  # NEW (Task 19): running cost + history widget
├── tools/
│   ├── measure_stats.py             # NEW (Task 1): copied from the starter zip, unchanged
│   └── grain_metric.py               # NEW (Task 1): copied from the starter zip, unchanged
└── tests/
    ├── test_layout_and_filter.py     # NEW (Task 1): copied from the starter zip, unchanged
    ├── test_detection.py              # NEW (Task 2)
    ├── test_triage.py                  # NEW (Task 3)
    ├── test_crop.py                     # NEW (Task 4)
    ├── test_providers.py                # NEW (Task 5, 6)
    ├── test_cost.py                      # NEW (Task 7)
    ├── test_decision_log.py              # NEW (Task 8)
    ├── test_settings.py                   # NEW (Task 9)
    ├── test_pipeline.py                    # NEW (Task 10)
    ├── test_crop_editor_state.py            # NEW (Task 17)
    └── test_gui_smoke.py                     # NEW (Task 21)
```

All `src/` modules are flat top-level modules imported via the same `sys.path.insert(0, ".../src")` pattern the existing `tests/test_layout_and_filter.py` already uses (there is no `src/__init__.py` — following the existing codebase's own convention). `src/providers/` is the one subpackage (it needs its own `__init__.py`), reached as `from providers.base import ...` once `src/` is on `sys.path`.

---

## Task 1: Import the starter pipeline into this repo

**Files:**
- Create: `requirements.txt`
- Create: `src/hp5_emulate.py`
- Create: `tests/test_layout_and_filter.py`
- Create: `tools/measure_stats.py`
- Create: `tools/grain_metric.py`
- Create: `docs/pipeline-brief.md`
- Create: `docs/filter_hp5_notes.md`
- Create: `docs/reference_stats.json`

**Interfaces:**
- Produces: `src/hp5_emulate.py` exposing (unchanged from the starter): `PARAMS: dict`, `SHAPES: dict`, `layout(shape, canvas_long=2400, border_frac=None) -> dict` (keys `canvas`, `border`, `inner`, `inner_ratio`), `emulate(img: PIL.Image, seed=0, p=PARAMS) -> PIL.Image`, `add_border(img, frac, value=255) -> PIL.Image`, `center_crop(img, ratio) -> PIL.Image`, `render(cropped, shape, canvas_long=2400, seed=0) -> PIL.Image`, `process_file(...)`, `tone_curve(y, p)`.

This task has no failing-test step of its own (it's importing already-tested code) — its test cycle is "the existing suite still passes verbatim."

- [ ] **Step 1: Copy the starter files into this repo**

The starter package is at `C:\Users\vibha\AppData\Local\Temp\claude\C--new-projects-Cropper\5b6d724e-3894-4855-bfe7-3ff3b5c0afa9\scratchpad\photo-pipeline-starter\photo-pipeline-starter` (extracted from the user's `photo-pipeline-starter.zip`). Copy these files **byte-for-byte unchanged**:
- `src/hp5_emulate.py` → `src/hp5_emulate.py`
- `tests/test_layout_and_filter.py` → `tests/test_layout_and_filter.py`
- `tools/measure_stats.py` → `tools/measure_stats.py`
- `tools/grain_metric.py` → `tools/grain_metric.py`
- `docs/filter_hp5_notes.md` → `docs/filter_hp5_notes.md`
- `docs/reference_stats.json` → `docs/reference_stats.json`
- `CLAUDE.md` → `docs/pipeline-brief.md` (renamed — this repo already has its own `CLAUDE.md` for agent-skills config; do not overwrite it)

Add one line at the top of the new `docs/pipeline-brief.md`, above its existing `# Travel photo batch pipeline: crop, filter, border` heading:

```markdown
> Note: this was the project brief from the original `photo-pipeline-starter.zip` (that
> package's own `CLAUDE.md`). It lives here, not at the repo root, because this repo's
> `CLAUDE.md` is a different document (agent-skills config). See `.scratch/desktop-tool/spec.md`
> for the desktop tool requirements that supersede this brief's "Suggested first steps" section.
```

- [ ] **Step 2: Write `requirements.txt`**

```
numpy==2.5.3
scipy==1.18.1
Pillow==12.3.0
PySide6==6.11.2
opencv-contrib-python==4.11.0.86
openai==3.16.2
keyring==25.7.0
```

- [ ] **Step 3: Install dependencies and run the existing test suite**

Run: `pip install -r requirements.txt`
Then run: `python -m unittest discover -s tests -v`
Expected: all 10 existing tests pass (`test_process_file_shape_mode`, `test_canvas_ratios`, `test_canvas_sizes_and_border`, `test_inner_ratio_differs_from_canvas_ratio`, `test_deterministic_for_same_seed`, `test_render_exact_canvas_and_pure_white_border`, `test_render_rejects_wrong_ratio`, `test_upscale_warns`, `test_curve_monotonic_with_floor_and_soft_ceiling`, `test_output_highlights_stay_below_clip`).

- [ ] **Step 4: Commit**

```bash
git add requirements.txt src/hp5_emulate.py tests/test_layout_and_filter.py tools/measure_stats.py tools/grain_metric.py docs/pipeline-brief.md docs/filter_hp5_notes.md docs/reference_stats.json
git commit -m "Import starter photo pipeline (filter, layout, tests) into Cropper repo"
```

---

## Task 2: Detection module (faces, saliency, symmetry)

**Files:**
- Create: `src/detection.py`
- Test: `tests/test_detection.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (uses `cv2`, `numpy` only).
- Produces: `FaceBox(x: int, y: int, w: int, h: int)` (dataclass, `.area` property), `SaliencyResult(heatmap: np.ndarray, blob_fraction: float, touches_edge: bool)` (dataclass), `DetectionResult(faces: list[FaceBox], saliency: SaliencyResult, symmetry_score: float)` (dataclass), `detect_faces(gray: np.ndarray) -> list[FaceBox]`, `saliency_map(bgr: np.ndarray, blob_threshold: float = 0.5) -> SaliencyResult`, `symmetry_score(gray: np.ndarray) -> float`, `detect(bgr: np.ndarray) -> DetectionResult`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_detection.py
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import detection as D  # noqa: E402


def synthetic_symmetric(w=200, h=160):
    img = np.zeros((h, w), dtype=np.uint8)
    half = w // 2
    ramp = np.linspace(0, 255, half, dtype=np.uint8)
    img[:, :half] = ramp[None, :]
    img[:, half:half + half] = ramp[None, ::-1][:, :img[:, half:].shape[1]]
    return img


def synthetic_asymmetric(w=200, h=160):
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, size=(h, w), dtype=np.uint8)


class SymmetryTests(unittest.TestCase):
    def test_symmetric_image_scores_high(self):
        self.assertGreater(D.symmetry_score(synthetic_symmetric()), 0.9)

    def test_random_image_scores_lower(self):
        sym = D.symmetry_score(synthetic_symmetric())
        rand = D.symmetry_score(synthetic_asymmetric())
        self.assertLess(rand, sym)


class SaliencyTests(unittest.TestCase):
    def test_saliency_map_shape_and_range(self):
        bgr = np.zeros((120, 160, 3), dtype=np.uint8)
        bgr[40:80, 60:100] = 255
        result = D.saliency_map(bgr)
        self.assertEqual(result.heatmap.shape, (120, 160))
        self.assertTrue((result.heatmap >= 0).all() and (result.heatmap <= 1).all())
        self.assertIsInstance(result.blob_fraction, float)
        self.assertIsInstance(result.touches_edge, bool)

    def test_whole_frame_bright_blob_touches_edge(self):
        bgr = np.full((100, 100, 3), 255, dtype=np.uint8)
        result = D.saliency_map(bgr, blob_threshold=0.1)
        self.assertTrue(result.touches_edge)


class FaceDetectionTests(unittest.TestCase):
    def test_no_faces_in_blank_image(self):
        gray = np.zeros((200, 200), dtype=np.uint8)
        self.assertEqual(D.detect_faces(gray), [])


class DetectTests(unittest.TestCase):
    def test_detect_returns_full_result(self):
        bgr = np.zeros((120, 160, 3), dtype=np.uint8)
        result = D.detect(bgr)
        self.assertIsInstance(result, D.DetectionResult)
        self.assertIsInstance(result.faces, list)
        self.assertIsInstance(result.saliency, D.SaliencyResult)
        self.assertIsInstance(result.symmetry_score, float)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_detection -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'detection'`.

- [ ] **Step 3: Write `src/detection.py`**

```python
"""Detection pass: face detection (Haar cascade), saliency mapping (spectral
residual), and a symmetry test (mirror-flip comparison). No tilt or perspective
correction - the pipeline brief assumes photos are shot at the intended
orientation and only crops."""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def area(self) -> int:
        return self.w * self.h


@dataclass(frozen=True)
class SaliencyResult:
    heatmap: np.ndarray
    blob_fraction: float
    touches_edge: bool


@dataclass(frozen=True)
class DetectionResult:
    faces: list
    saliency: SaliencyResult
    symmetry_score: float


_FACE_CASCADE = None


def _face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _FACE_CASCADE = cv2.CascadeClassifier(path)
    return _FACE_CASCADE


def detect_faces(gray: np.ndarray) -> list:
    boxes = _face_cascade().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
    )
    return [FaceBox(int(x), int(y), int(w), int(h)) for (x, y, w, h) in boxes]


def saliency_map(bgr: np.ndarray, blob_threshold: float = 0.5) -> SaliencyResult:
    saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
    success, heatmap = saliency.computeSaliency(bgr)
    if not success:
        raise RuntimeError("saliency computation failed")
    heatmap = heatmap.astype(np.float32)
    mask = heatmap >= blob_threshold
    blob_fraction = float(mask.mean())
    h, w = mask.shape
    edge_band = max(1, round(0.03 * max(h, w)))
    touches_edge = bool(
        mask[:edge_band, :].any() or mask[-edge_band:, :].any()
        or mask[:, :edge_band].any() or mask[:, -edge_band:].any()
    )
    return SaliencyResult(heatmap=heatmap, blob_fraction=blob_fraction, touches_edge=touches_edge)


def symmetry_score(gray: np.ndarray) -> float:
    flipped = np.fliplr(gray)
    diff = np.abs(gray.astype(np.float32) - flipped.astype(np.float32))
    return float(1.0 - diff.mean() / 255.0)


def detect(bgr: np.ndarray) -> DetectionResult:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    faces = detect_faces(gray)
    sal = saliency_map(bgr)
    sym = symmetry_score(gray)
    return DetectionResult(faces=faces, saliency=sal, symmetry_score=sym)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_detection -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/detection.py tests/test_detection.py
git commit -m "Add detection module: faces, saliency, symmetry"
```

---

## Task 3: Triage module

**Files:**
- Create: `src/triage.py`
- Test: `tests/test_triage.py`

**Interfaces:**
- Consumes: `detection.DetectionResult`, `detection.FaceBox`, `detection.SaliencyResult` (Task 2).
- Produces: `THRESHOLDS: dict` (keys `saliency_blob_max`, `symmetry_ambiguous_low`, `symmetry_ambiguous_high`), `TriageDecision(escalate: bool, reasons: list[str])` (dataclass), `triage(detection: DetectionResult, image_area: int, thresholds: dict = THRESHOLDS) -> TriageDecision`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_triage.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import triage as T  # noqa: E402
from detection import DetectionResult, FaceBox, SaliencyResult  # noqa: E402


def make_detection(faces=None, blob_fraction=0.1, touches_edge=False, symmetry_score=0.95):
    import numpy as np
    return DetectionResult(
        faces=faces or [],
        saliency=SaliencyResult(heatmap=np.zeros((10, 10), dtype="float32"),
                                 blob_fraction=blob_fraction, touches_edge=touches_edge),
        symmetry_score=symmetry_score,
    )


class TriageTests(unittest.TestCase):
    def test_clear_photo_does_not_escalate(self):
        d = make_detection(faces=[FaceBox(10, 10, 50, 50)], blob_fraction=0.1,
                            touches_edge=False, symmetry_score=0.95)
        decision = T.triage(d, image_area=100 * 100)
        self.assertFalse(decision.escalate)
        self.assertEqual(decision.reasons, [])

    def test_whole_frame_saliency_escalates(self):
        d = make_detection(blob_fraction=0.9)
        decision = T.triage(d, image_area=100 * 100)
        self.assertTrue(decision.escalate)
        self.assertIn("saliency spans nearly the whole frame", decision.reasons)

    def test_multiple_faces_no_clear_primary_escalates(self):
        d = make_detection(faces=[FaceBox(0, 0, 50, 50), FaceBox(60, 60, 48, 48)])
        decision = T.triage(d, image_area=100 * 100)
        self.assertTrue(decision.escalate)
        self.assertIn("multiple faces with no clear primary subject", decision.reasons)

    def test_multiple_faces_with_clear_primary_does_not_escalate_for_that_reason(self):
        d = make_detection(faces=[FaceBox(0, 0, 80, 80), FaceBox(90, 90, 10, 10)])
        decision = T.triage(d, image_area=100 * 100)
        self.assertNotIn("multiple faces with no clear primary subject", decision.reasons)

    def test_edge_touching_blob_escalates(self):
        d = make_detection(touches_edge=True)
        decision = T.triage(d, image_area=100 * 100)
        self.assertTrue(decision.escalate)
        self.assertIn("saliency blob touches an edge or corner", decision.reasons)

    def test_ambiguous_symmetry_escalates(self):
        d = make_detection(symmetry_score=0.65)
        decision = T.triage(d, image_area=100 * 100)
        self.assertTrue(decision.escalate)
        self.assertIn("symmetry score is ambiguous", decision.reasons)

    def test_decisive_low_symmetry_does_not_escalate_for_that_reason(self):
        d = make_detection(symmetry_score=0.1)
        decision = T.triage(d, image_area=100 * 100)
        self.assertNotIn("symmetry score is ambiguous", decision.reasons)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_triage -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'triage'`.

- [ ] **Step 3: Write `src/triage.py`**

```python
"""Triage gate: decide per photo whether to escalate to paid AI reasoning or
handle it with the formula crop. THRESHOLDS are initial guesses - like PARAMS
in hp5_emulate.py, tune them against labeled real batches, not eyeballed."""
from dataclasses import dataclass

THRESHOLDS = dict(
    saliency_blob_max=0.85,
    symmetry_ambiguous_low=0.55,
    symmetry_ambiguous_high=0.80,
)


@dataclass(frozen=True)
class TriageDecision:
    escalate: bool
    reasons: list


def triage(detection, image_area: int, thresholds: dict = THRESHOLDS) -> TriageDecision:
    reasons = []
    if detection.saliency.blob_fraction >= thresholds["saliency_blob_max"]:
        reasons.append("saliency spans nearly the whole frame")
    if len(detection.faces) >= 2:
        areas = sorted((f.area for f in detection.faces), reverse=True)
        if areas[0] < 1.5 * areas[1]:
            reasons.append("multiple faces with no clear primary subject")
    if detection.saliency.touches_edge:
        reasons.append("saliency blob touches an edge or corner")
    if thresholds["symmetry_ambiguous_low"] <= detection.symmetry_score <= thresholds["symmetry_ambiguous_high"]:
        reasons.append("symmetry score is ambiguous")
    return TriageDecision(escalate=bool(reasons), reasons=reasons)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_triage -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/triage.py tests/test_triage.py
git commit -m "Add triage gate module"
```

---

## Task 4: Formula crop module

**Files:**
- Create: `src/crop.py`
- Test: `tests/test_crop.py`

**Interfaces:**
- Consumes: `detection.FaceBox` (Task 2, for type reference only — `formula_crop` takes a plain `list` of objects with `.x .y .w .h .area`).
- Produces: `CropBox(x0: float, y0: float, x1: float, y1: float)` (dataclass, fractions of source width/height, `.to_pixels(img_w, img_h) -> tuple[int, int, int, int]`), `formula_crop(img_w: int, img_h: int, inner_ratio: float, faces: list, symmetric: bool) -> CropBox`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_crop.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import crop as C  # noqa: E402
from detection import FaceBox  # noqa: E402


class CropBoxTests(unittest.TestCase):
    def test_to_pixels(self):
        box = C.CropBox(0.25, 0.25, 0.75, 0.75)
        self.assertEqual(box.to_pixels(400, 200), (100, 50, 300, 150))


class FormulaCropTests(unittest.TestCase):
    def test_crop_ratio_matches_inner_ratio(self):
        box = C.formula_crop(4000, 3000, inner_ratio=0.7917, faces=[], symmetric=False)
        x0, y0, x1, y1 = box.to_pixels(4000, 3000)
        w, h = x1 - x0, y1 - y0
        self.assertAlmostEqual(w / h, 0.7917, delta=0.005)

    def test_no_face_centers_on_image(self):
        box = C.formula_crop(1000, 1000, inner_ratio=1.0, faces=[], symmetric=False)
        x0, y0, x1, y1 = box.to_pixels(1000, 1000)
        self.assertAlmostEqual((x0 + x1) / 2, 500, delta=1)
        self.assertAlmostEqual((y0 + y1) / 2, 500, delta=1)

    def test_symmetric_subject_is_centered_regardless_of_face_position(self):
        faces = [FaceBox(100, 100, 50, 50)]
        box = C.formula_crop(1000, 1000, inner_ratio=1.0, faces=faces, symmetric=True)
        x0, y0, x1, y1 = box.to_pixels(1000, 1000)
        self.assertAlmostEqual((x0 + x1) / 2, 500, delta=1)
        self.assertAlmostEqual((y0 + y1) / 2, 500, delta=1)

    def test_off_center_face_pulls_crop_toward_a_third_line(self):
        # 1500x1000 image, square crop (inner_ratio=1.0) leaves 500px of horizontal
        # slack (crop_w=1000 < img_w=1500) for the crop to actually shift - a square
        # crop of a square image would have zero slack on either axis and could
        # never be off-center regardless of face position, so this must be
        # rectangular for the test to be satisfiable at all.
        faces = [FaceBox(50, 450, 100, 100)]  # face in the left portion of the frame
        box = C.formula_crop(1500, 1000, inner_ratio=1.0, faces=faces, symmetric=False)
        x0, y0, x1, y1 = box.to_pixels(1500, 1000)
        crop_center_x = (x0 + x1) / 2
        self.assertLess(crop_center_x, 750)  # not centered on the full 1500-wide image

    def test_crop_stays_within_source_bounds(self):
        faces = [FaceBox(0, 0, 20, 20)]
        box = C.formula_crop(1000, 800, inner_ratio=0.8, faces=faces, symmetric=False)
        x0, y0, x1, y1 = box.to_pixels(1000, 800)
        self.assertGreaterEqual(x0, 0)
        self.assertGreaterEqual(y0, 0)
        self.assertLessEqual(x1, 1000)
        self.assertLessEqual(y1, 800)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_crop -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'crop'`.

- [ ] **Step 3: Write `src/crop.py`**

```python
"""Formula crop: rule-of-thirds and symmetry math for non-escalated photos.
Subject position is computed as an exact fraction of the crop and checked
against the 1/3 and 2/3 targets - not eyeballed. Symmetric subjects (e.g. a
centered facade) are centered instead of placed on a thirds line."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CropBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def to_pixels(self, img_w: int, img_h: int) -> tuple:
        return (round(self.x0 * img_w), round(self.y0 * img_h),
                round(self.x1 * img_w), round(self.y1 * img_h))


def _subject_center_px(img_w: int, img_h: int, faces: list) -> tuple:
    if not faces:
        return (img_w / 2, img_h / 2)
    best = max(faces, key=lambda f: f.area)
    return (best.x + best.w / 2, best.y + best.h / 2)


def formula_crop(img_w: int, img_h: int, inner_ratio: float, faces: list, symmetric: bool) -> CropBox:
    src_ratio = img_w / img_h
    if src_ratio > inner_ratio:
        crop_h = img_h
        crop_w = round(crop_h * inner_ratio)
    else:
        crop_w = img_w
        crop_h = round(crop_w / inner_ratio)

    if symmetric:
        center_x_px, center_y_px = img_w / 2, img_h / 2
        target_x, target_y = 0.5, 0.5
    else:
        center_x_px, center_y_px = _subject_center_px(img_w, img_h, faces)
        target_x = 1 / 3 if center_x_px < img_w / 2 else 2 / 3
        target_y = 1 / 3 if center_y_px < img_h / 2 else 2 / 3

    left = center_x_px - target_x * crop_w
    top = center_y_px - target_y * crop_h
    left = max(0, min(left, img_w - crop_w))
    top = max(0, min(top, img_h - crop_h))

    return CropBox(
        x0=left / img_w, y0=top / img_h,
        x1=(left + crop_w) / img_w, y1=(top + crop_h) / img_h,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_crop -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/crop.py tests/test_crop.py
git commit -m "Add formula crop module (rule of thirds / symmetry)"
```

---

## Task 5: Provider-agnostic escalation interface

**Files:**
- Create: `src/providers/__init__.py`
- Create: `src/providers/base.py`
- Test: `tests/test_providers.py` (created here, extended in Task 6)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `CropDecision(crop_box: tuple, confidence: float, tier: str)` (dataclass, `crop_box` is `(x0, y0, x1, y1)` fractions), `CropProvider` (ABC with `name` property, `price_per_million_tokens(tier: str) -> tuple[float, float]`, `request_crop(image_bytes: bytes, detection_metadata: dict, inner_ratio: float, tier: str) -> CropDecision`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_providers.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from providers.base import CropProvider, CropDecision  # noqa: E402


class DummyProvider(CropProvider):
    @property
    def name(self):
        return "dummy"

    def price_per_million_tokens(self, tier):
        return (1.0, 2.0)

    def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
        return CropDecision(crop_box=(0.1, 0.1, 0.9, 0.9), confidence=0.8, tier=tier)


class CropProviderInterfaceTests(unittest.TestCase):
    def test_cannot_instantiate_abstract_base(self):
        with self.assertRaises(TypeError):
            CropProvider()

    def test_concrete_provider_implements_interface(self):
        p = DummyProvider()
        self.assertEqual(p.name, "dummy")
        self.assertEqual(p.price_per_million_tokens("cheap"), (1.0, 2.0))
        decision = p.request_crop(b"", {}, 0.8, "cheap")
        self.assertEqual(decision.tier, "cheap")
        self.assertEqual(decision.crop_box, (0.1, 0.1, 0.9, 0.9))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_providers -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'providers'`.

- [ ] **Step 3: Write `src/providers/__init__.py` and `src/providers/base.py`**

`src/providers/__init__.py`:
```python
```
(empty — marks `providers` as a package)

`src/providers/base.py`:
```python
"""Provider-agnostic interface for the escalated crop decision: one combined
call per photo, image + detection metadata in, crop decision + confidence out.
Any vision-capable model with structured/JSON output can implement this."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CropDecision:
    crop_box: tuple  # (x0, y0, x1, y1) as fractions of image width/height, 0..1
    confidence: float  # 0..1
    tier: str  # "cheap" or "strong"


class CropProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def price_per_million_tokens(self, tier: str) -> tuple:
        """Return (input_price, output_price) in USD per 1,000,000 tokens for this tier."""
        ...

    @abstractmethod
    def request_crop(self, image_bytes: bytes, detection_metadata: dict,
                      inner_ratio: float, tier: str) -> CropDecision:
        ...
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_providers -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/providers/__init__.py src/providers/base.py tests/test_providers.py
git commit -m "Add provider-agnostic crop escalation interface"
```

---

## Task 6: OpenAI provider implementation

**Files:**
- Create: `src/providers/openai_provider.py`
- Modify: `tests/test_providers.py` (append tests)

**Interfaces:**
- Consumes: `providers.base.CropProvider`, `providers.base.CropDecision` (Task 5).
- Produces: `OpenAICropProvider(client=None)` — `.name == "openai"`, `.price_per_million_tokens(tier) -> tuple`, `.request_crop(image_bytes, detection_metadata, inner_ratio, tier) -> CropDecision`. Reads `OPENAI_API_KEY` from the environment via the `openai` SDK's own default client behavior when `client` is not injected.

Verified against the current OpenAI API docs (2026-09-20): vision input uses `client.responses.create(model=..., input=[{"role": "user", "content": [{"type": "input_text", ...}, {"type": "input_image", "image_url": "data:image/jpeg;base64,..."}]}], text={"format": {"type": "json_schema", "name": ..., "schema": {...}, "strict": True}})`; the JSON result is on `response.output_text`. Current vision-capable models/pricing per 1M tokens: `gpt-4o-mini` ($0.15 in / $0.60 out) as the cheap tier, `gpt-6-astra` ($10.00 in / $50.00 out) as the strong tier.

- [ ] **Step 1: Write the failing tests (appended to `tests/test_providers.py`)**

Append to `tests/test_providers.py` (keep the existing imports and `DummyProvider`/`CropProviderInterfaceTests` class untouched):

```python
import json
from unittest.mock import MagicMock

from providers.openai_provider import OpenAICropProvider  # noqa: E402


class FakeResponses:
    def __init__(self, payload):
        self._payload = payload
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        response = MagicMock()
        response.output_text = json.dumps(self._payload)
        return response


class FakeOpenAIClient:
    def __init__(self, payload):
        self.responses = FakeResponses(payload)


class OpenAICropProviderTests(unittest.TestCase):
    def test_name(self):
        provider = OpenAICropProvider(client=FakeOpenAIClient({}))
        self.assertEqual(provider.name, "openai")

    def test_pricing_cheap_and_strong_differ(self):
        provider = OpenAICropProvider(client=FakeOpenAIClient({}))
        cheap = provider.price_per_million_tokens("cheap")
        strong = provider.price_per_million_tokens("strong")
        self.assertLess(cheap[0], strong[0])
        self.assertLess(cheap[1], strong[1])

    def test_request_crop_parses_response_into_crop_decision(self):
        payload = {"x0": 0.1, "y0": 0.2, "x1": 0.9, "y1": 0.8, "confidence": 0.73}
        fake_client = FakeOpenAIClient(payload)
        provider = OpenAICropProvider(client=fake_client)
        decision = provider.request_crop(b"fakejpegbytes", {"faces": []}, 0.8, "cheap")
        self.assertEqual(decision.crop_box, (0.1, 0.2, 0.9, 0.8))
        self.assertAlmostEqual(decision.confidence, 0.73)
        self.assertEqual(decision.tier, "cheap")

    def test_request_crop_sends_image_and_json_schema(self):
        payload = {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 1.0, "confidence": 0.5}
        fake_client = FakeOpenAIClient(payload)
        provider = OpenAICropProvider(client=fake_client)
        provider.request_crop(b"fakejpegbytes", {"faces": []}, 0.8, "strong")
        kwargs = fake_client.responses.last_call_kwargs
        self.assertEqual(kwargs["model"], "gpt-6-astra")
        content = kwargs["input"][0]["content"]
        self.assertTrue(any(c["type"] == "input_image" for c in content))
        self.assertEqual(kwargs["text"]["format"]["type"], "json_schema")
        self.assertTrue(kwargs["text"]["format"]["strict"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_providers -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'providers.openai_provider'`.

- [ ] **Step 3: Write `src/providers/openai_provider.py`**

```python
"""OpenAI implementation of the provider-agnostic crop escalation interface.
API shape verified against platform.openai.com docs on 2026-09-20."""
import base64
import json

from openai import OpenAI

from .base import CropProvider, CropDecision

_SCHEMA = {
    "type": "object",
    "properties": {
        "x0": {"type": "number"},
        "y0": {"type": "number"},
        "x1": {"type": "number"},
        "y1": {"type": "number"},
        "confidence": {"type": "number"},
    },
    "required": ["x0", "y0", "x1", "y1", "confidence"],
    "additionalProperties": False,
}

_MODELS = {"cheap": "gpt-4o-mini", "strong": "gpt-6-astra"}

# USD per 1,000,000 tokens: (input, output). Confirmed at platform.openai.com/docs/pricing
# on 2026-09-20 - re-verify before relying on these for a real spend decision much later.
_PRICES = {
    "cheap": (0.15, 0.60),
    "strong": (10.00, 50.00),
}


class OpenAICropProvider(CropProvider):
    def __init__(self, client=None):
        self._client = client if client is not None else OpenAI()

    @property
    def name(self) -> str:
        return "openai"

    def price_per_million_tokens(self, tier: str) -> tuple:
        return _PRICES[tier]

    def request_crop(self, image_bytes: bytes, detection_metadata: dict,
                      inner_ratio: float, tier: str) -> CropDecision:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        prompt = (
            "You are choosing a crop for a travel photo. The crop must have width:height "
            f"ratio {inner_ratio:.4f}. Detection metadata (faces, saliency, symmetry) is "
            f"provided as JSON: {json.dumps(detection_metadata)}. Return the crop box as "
            "fractions of the full image (x0,y0,x1,y1, each 0..1, x1>x0, y1>y0) and your "
            "confidence (0..1) that this is the best composition."
        )
        response = self._client.responses.create(
            model=_MODELS[tier],
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
                ],
            }],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "crop_decision",
                    "schema": _SCHEMA,
                    "strict": True,
                }
            },
        )
        data = json.loads(response.output_text)
        return CropDecision(
            crop_box=(data["x0"], data["y0"], data["x1"], data["y1"]),
            confidence=data["confidence"],
            tier=tier,
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_providers -v`
Expected: all 6 tests PASS (2 from Task 5 + 4 new).

- [ ] **Step 5: Commit**

```bash
git add src/providers/openai_provider.py tests/test_providers.py
git commit -m "Add OpenAI crop provider implementation"
```

---

## Task 7: Cost estimation module

**Files:**
- Create: `src/cost.py`
- Test: `tests/test_cost.py`

**Interfaces:**
- Consumes: `providers.base.CropProvider` (Task 5) — takes any object with `.price_per_million_tokens(tier)`.
- Produces: `APPROX_INPUT_TOKENS_PER_CALL: int`, `APPROX_OUTPUT_TOKENS_PER_CALL: int`, `estimate_call_cost(provider, tier: str) -> float`, `estimate_worst_case_batch_cost(provider, num_flagged_photos: int) -> float`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cost.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import cost as C  # noqa: E402


class FakeProvider:
    def price_per_million_tokens(self, tier):
        return {"cheap": (0.15, 0.60), "strong": (10.00, 50.00)}[tier]


class CostTests(unittest.TestCase):
    def test_call_cost_is_positive_and_scales_with_tier(self):
        provider = FakeProvider()
        cheap = C.estimate_call_cost(provider, "cheap")
        strong = C.estimate_call_cost(provider, "strong")
        self.assertGreater(cheap, 0)
        self.assertGreater(strong, cheap)

    def test_worst_case_batch_cost_assumes_strong_tier_for_every_photo(self):
        provider = FakeProvider()
        single_strong = C.estimate_call_cost(provider, "strong")
        batch = C.estimate_worst_case_batch_cost(provider, 5)
        self.assertAlmostEqual(batch, 5 * single_strong)

    def test_zero_flagged_photos_costs_nothing(self):
        provider = FakeProvider()
        self.assertEqual(C.estimate_worst_case_batch_cost(provider, 0), 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_cost -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cost'`.

- [ ] **Step 3: Write `src/cost.py`**

```python
"""Cost estimation for escalated crop calls. Always used as a worst-case upper
bound (every flagged photo assumed to need the stronger/pricier tier) before
any paid call runs - see the desktop tool spec's cost-gating requirement."""

# Approximate tokens per escalation call: one downscaled image plus prompt text
# for input, a small JSON crop decision for output. This is a documented
# approximation, not measured - refine against response.usage once the
# escalation step has actually run on real photos.
APPROX_INPUT_TOKENS_PER_CALL = 1700
APPROX_OUTPUT_TOKENS_PER_CALL = 100


def estimate_call_cost(provider, tier: str) -> float:
    input_price, output_price = provider.price_per_million_tokens(tier)
    return (
        (APPROX_INPUT_TOKENS_PER_CALL / 1_000_000) * input_price
        + (APPROX_OUTPUT_TOKENS_PER_CALL / 1_000_000) * output_price
    )


def estimate_worst_case_batch_cost(provider, num_flagged_photos: int) -> float:
    return num_flagged_photos * estimate_call_cost(provider, "strong")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_cost -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cost.py tests/test_cost.py
git commit -m "Add worst-case cost estimation module"
```

---

## Task 8: Decision log module

**Files:**
- Create: `src/decision_log.py`
- Test: `tests/test_decision_log.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `DecisionRecord(photo_name: str, escalated: bool, tier: str, provider: str, cost: float, confidence: float, timestamp: float)` (dataclass), `DecisionLog(path: pathlib.Path)` — `.records: list[DecisionRecord]`, `.add(record: DecisionRecord) -> None`, `.running_cost: float` (property).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_decision_log.py
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import decision_log as DL  # noqa: E402


class DecisionLogTests(unittest.TestCase):
    def test_new_log_starts_empty(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(Path(d) / "log.jsonl")
            self.assertEqual(log.records, [])
            self.assertEqual(log.running_cost, 0.0)

    def test_add_appends_and_persists(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "log.jsonl"
            log = DL.DecisionLog(path)
            record = DL.DecisionRecord(photo_name="a.jpg", escalated=True, tier="cheap",
                                        provider="openai", cost=0.001, confidence=0.9,
                                        timestamp=1.0)
            log.add(record)
            self.assertEqual(len(log.records), 1)
            self.assertAlmostEqual(log.running_cost, 0.001)
            self.assertTrue(path.exists())

    def test_reloading_reads_previous_records(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "log.jsonl"
            log1 = DL.DecisionLog(path)
            log1.add(DL.DecisionRecord(photo_name="a.jpg", escalated=False, tier="",
                                        provider="", cost=0.0, confidence=-1.0, timestamp=1.0))
            log1.add(DL.DecisionRecord(photo_name="b.jpg", escalated=True, tier="strong",
                                        provider="openai", cost=0.05, confidence=0.4,
                                        timestamp=2.0))
            log2 = DL.DecisionLog(path)
            self.assertEqual(len(log2.records), 2)
            self.assertAlmostEqual(log2.running_cost, 0.05)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_decision_log -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'decision_log'`.

- [ ] **Step 3: Write `src/decision_log.py`**

```python
"""Per-photo decision log: which photos escalated, which model/tier handled
it, and cost. Visible in-app as a running total and history list (the
pipeline brief's open item #7 - a per-photo decision log for tuning triage
thresholds on real batches)."""
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class DecisionRecord:
    photo_name: str
    escalated: bool
    tier: str
    provider: str
    cost: float
    confidence: float
    timestamp: float


class DecisionLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.records = []
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.records.append(DecisionRecord(**json.loads(line)))

    def add(self, record: DecisionRecord) -> None:
        self.records.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    @property
    def running_cost(self) -> float:
        return sum(r.cost for r in self.records)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_decision_log -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/decision_log.py tests/test_decision_log.py
git commit -m "Add per-photo decision log with running cost"
```

---

## Task 9: Settings persistence module

**Files:**
- Create: `src/settings.py`
- Test: `tests/test_settings.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `AppSettings(shape: str = "square", canvas_long: int = 2400, apply_filter: bool = True, last_input_folder: str = "", last_output_folder: str = "")` (dataclass), `AppSettings.load(path: pathlib.Path) -> AppSettings` (classmethod), `AppSettings.save(self, path: pathlib.Path) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_settings.py
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import settings as S  # noqa: E402


class AppSettingsTests(unittest.TestCase):
    def test_load_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            loaded = S.AppSettings.load(Path(d) / "missing.json")
            self.assertEqual(loaded.shape, "square")
            self.assertEqual(loaded.canvas_long, 2400)
            self.assertTrue(loaded.apply_filter)

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            original = S.AppSettings(shape="portrait", canvas_long=1800, apply_filter=False,
                                      last_input_folder="C:/photos", last_output_folder="C:/out")
            original.save(path)
            loaded = S.AppSettings.load(path)
            self.assertEqual(loaded, original)

    def test_load_ignores_unknown_fields_gracefully(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            path.write_text('{"shape": "landscape", "canvas_long": 3000, "extra_junk": 1}',
                             encoding="utf-8")
            loaded = S.AppSettings.load(path)
            self.assertEqual(loaded.shape, "landscape")
            self.assertEqual(loaded.canvas_long, 3000)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_settings -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'settings'`.

- [ ] **Step 3: Write `src/settings.py`**

```python
"""Persisted app settings (shape, canvas size, filter toggle, last input/output
folders) across restarts, stored as a small local JSON file."""
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppSettings:
    shape: str = "square"
    canvas_long: int = 2400
    apply_filter: bool = True
    last_input_folder: str = ""
    last_output_folder: str = ""

    @classmethod
    def load(cls, path: Path) -> "AppSettings":
        path = Path(path)
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        known = {k: v for k, v in data.items() if k in asdict(cls())}
        return cls(**known)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_settings -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/settings.py tests/test_settings.py
git commit -m "Add persisted app settings module"
```

---

## Task 10: Pipeline orchestration

**Files:**
- Create: `src/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `hp5_emulate.layout`, `hp5_emulate.emulate` (existing, Task 1); `detection.detect`, `detection.DetectionResult` (Task 2); `triage.triage`, `triage.THRESHOLDS`, `triage.TriageDecision` (Task 3); `crop.formula_crop`, `crop.CropBox` (Task 4); `providers.base.CropProvider`, `providers.base.CropDecision` (Task 5).
- Produces: `PhotoJob` (dataclass: `src_path: str, filename: str, shape: str, canvas_long: int, apply_filter: bool, detection: DetectionResult|None, triage_decision: TriageDecision|None, crop_box: CropBox|None, crop_decision: CropDecision|None, rendered: PIL.Image|None, keep: bool, error: str|None`), `render_photo(img, crop_box, shape, canvas_long, apply_filter, seed) -> PIL.Image`, `process_photo(src_path: str, shape: str, canvas_long: int, apply_filter: bool) -> PhotoJob`, `process_folder(folder: str, shape: str, canvas_long: int, apply_filter: bool) -> Iterator[PhotoJob]`, `apply_escalation(job: PhotoJob, provider: CropProvider, tier: str) -> PhotoJob`, `apply_manual_crop(job: PhotoJob, crop_box: CropBox) -> PhotoJob`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline.py
import glob
import hashlib
import io
import os
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pipeline as P  # noqa: E402
from crop import CropBox  # noqa: E402
from providers.base import CropDecision  # noqa: E402


def synthetic_jpeg(path, w=800, h=600, seed=0):
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 255, w, dtype=np.float32)[None, :].repeat(h, 0)
    rgb = np.stack([x, x[::-1], np.full_like(x, 128)], -1) + rng.normal(0, 3, (h, w, 3))
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(path, quality=95)


class ProcessPhotoTests(unittest.TestCase):
    def test_process_photo_produces_rendered_image_matching_canvas_size(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            synthetic_jpeg(src)
            job = P.process_photo(src, shape="landscape", canvas_long=1200, apply_filter=True)
            self.assertIsNone(job.error)
            self.assertIsNotNone(job.rendered)
            import hp5_emulate as H
            self.assertEqual(job.rendered.size, H.layout("landscape", 1200)["canvas"])

    def test_process_photo_without_filter_skips_emulation(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            synthetic_jpeg(src)
            job = P.process_photo(src, shape="square", canvas_long=800, apply_filter=False)
            self.assertIsNone(job.error)
            self.assertEqual(job.rendered.mode, "L")

    def test_process_photo_sets_error_on_bad_file(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "not_an_image.jpg")
            with open(src, "wb") as f:
                f.write(b"not a jpeg")
            job = P.process_photo(src, shape="square", canvas_long=800, apply_filter=True)
            self.assertIsNotNone(job.error)
            self.assertIsNone(job.rendered)


class ProcessFolderTests(unittest.TestCase):
    def test_process_folder_yields_one_job_per_photo_and_skips_bad_ones(self):
        with tempfile.TemporaryDirectory() as d:
            synthetic_jpeg(os.path.join(d, "a.jpg"), seed=1)
            synthetic_jpeg(os.path.join(d, "b.jpg"), seed=2)
            with open(os.path.join(d, "c.jpg"), "wb") as f:
                f.write(b"corrupt")
            jobs = list(P.process_folder(d, shape="square", canvas_long=600, apply_filter=True))
            self.assertEqual(len(jobs), 3)
            errored = [j for j in jobs if j.error]
            ok = [j for j in jobs if not j.error]
            self.assertEqual(len(errored), 1)
            self.assertEqual(len(ok), 2)


class EscalationAndManualCropTests(unittest.TestCase):
    def test_apply_escalation_updates_crop_and_rerenders(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            synthetic_jpeg(src)
            job = P.process_photo(src, shape="square", canvas_long=600, apply_filter=True)
            original_rendered = job.rendered

            class FakeProvider:
                def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
                    return CropDecision(crop_box=(0.1, 0.1, 0.9, 0.9), confidence=0.77, tier=tier)

            updated = P.apply_escalation(job, FakeProvider(), "strong")
            self.assertEqual(updated.crop_decision.confidence, 0.77)
            self.assertEqual(updated.crop_decision.tier, "strong")
            self.assertIsNotNone(updated.rendered)
            self.assertNotEqual(np.asarray(updated.rendered).tobytes(),
                                 np.asarray(original_rendered).tobytes())

    def test_apply_manual_crop_rerenders_with_given_box(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            synthetic_jpeg(src)
            job = P.process_photo(src, shape="square", canvas_long=600, apply_filter=True)
            box = CropBox(0.0, 0.0, 1.0, 1.0)
            updated = P.apply_manual_crop(job, box)
            self.assertEqual(updated.crop_box, box)
            self.assertIsNotNone(updated.rendered)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_pipeline -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline'`.

- [ ] **Step 3: Write `src/pipeline.py`**

```python
"""Per-photo pipeline orchestration for the free/local stages (EXIF correction,
detection, triage, formula crop, filter, border) plus the explicit, separately
triggered paid escalation and manual-crop-override paths."""
import glob
import hashlib
import io
import os
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

import crop as crp
import detection as det
import hp5_emulate as H
import triage as tri


@dataclass
class PhotoJob:
    src_path: str
    filename: str
    shape: str
    canvas_long: int
    apply_filter: bool
    detection: object = None
    triage_decision: object = None
    crop_box: object = None
    crop_decision: object = None
    rendered: object = None
    keep: bool = False
    error: str = None


_PHOTO_EXTS = {".jpg", ".jpeg"}


def _seed_for(filename: str) -> int:
    return int(hashlib.md5(filename.encode()).hexdigest()[:8], 16)


def render_photo(img, crop_box, shape, canvas_long, apply_filter, seed):
    lay = H.layout(shape, canvas_long)
    iw, ih = lay["inner"]
    x0, y0, x1, y1 = crop_box.to_pixels(img.width, img.height)
    cropped = img.crop((x0, y0, x1, y1)).resize((iw, ih), Image.LANCZOS)
    out = H.emulate(cropped, seed) if apply_filter else cropped.convert("L")
    t = lay["border"]
    canvas = Image.new("L", lay["canvas"], 255)
    canvas.paste(out, (t, t))
    return canvas


def process_photo(src_path: str, shape: str, canvas_long: int, apply_filter: bool) -> PhotoJob:
    filename = os.path.basename(src_path)
    job = PhotoJob(src_path=src_path, filename=filename, shape=shape,
                   canvas_long=canvas_long, apply_filter=apply_filter)
    try:
        img = ImageOps.exif_transpose(Image.open(src_path)).convert("RGB")
        bgr = np.asarray(img)[:, :, ::-1].copy()
        job.detection = det.detect(bgr)
        job.triage_decision = tri.triage(job.detection, img.width * img.height)
        symmetric = job.detection.symmetry_score >= tri.THRESHOLDS["symmetry_ambiguous_high"]
        lay = H.layout(shape, canvas_long)
        job.crop_box = crp.formula_crop(img.width, img.height, lay["inner_ratio"],
                                         job.detection.faces, symmetric)
        seed = _seed_for(filename)
        job.rendered = render_photo(img, job.crop_box, shape, canvas_long, apply_filter, seed)
    except Exception as e:  # noqa: BLE001 - a single bad photo must not stop the batch
        job.error = str(e)
    return job


def process_folder(folder: str, shape: str, canvas_long: int, apply_filter: bool):
    paths = sorted(
        p for p in glob.glob(os.path.join(folder, "*"))
        if os.path.splitext(p)[1].lower() in _PHOTO_EXTS
    )
    for p in paths:
        yield process_photo(p, shape, canvas_long, apply_filter)


def apply_escalation(job: PhotoJob, provider, tier: str) -> PhotoJob:
    img = ImageOps.exif_transpose(Image.open(job.src_path)).convert("RGB")
    lay = H.layout(job.shape, job.canvas_long)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    metadata = {
        "faces": [dict(x=f.x, y=f.y, w=f.w, h=f.h) for f in job.detection.faces],
        "saliency_blob_fraction": job.detection.saliency.blob_fraction,
        "symmetry_score": job.detection.symmetry_score,
    }
    decision = provider.request_crop(buf.getvalue(), metadata, lay["inner_ratio"], tier)
    job.crop_decision = decision
    x0, y0, x1, y1 = decision.crop_box
    job.crop_box = crp.CropBox(x0, y0, x1, y1)
    seed = _seed_for(job.filename)
    job.rendered = render_photo(img, job.crop_box, job.shape, job.canvas_long,
                                 job.apply_filter, seed)
    return job


def apply_manual_crop(job: PhotoJob, crop_box) -> PhotoJob:
    img = ImageOps.exif_transpose(Image.open(job.src_path)).convert("RGB")
    seed = _seed_for(job.filename)
    job.crop_box = crop_box
    job.rendered = render_photo(img, crop_box, job.shape, job.canvas_long,
                                 job.apply_filter, seed)
    return job
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_pipeline -v`
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "Add pipeline orchestration tying detection/triage/crop/filter together"
```

---

## Task 11: CHECKPOINT — full engine test suite must pass before any GUI code

**Files:** none created or modified — verification only.

**Interfaces:** none.

- [ ] **Step 1: Run the entire test suite**

Run: `python -m unittest discover -s tests -v`
Expected: every test from Tasks 1–10 passes (existing 10 + detection 5 + triage 7 + crop 5 + providers 6 + cost 3 + decision_log 3 + settings 3 + pipeline 6 = 48 tests, 0 failures).

- [ ] **Step 2: If anything fails, stop and fix it here**

Do not proceed to Task 12 (GUI work) until this run is clean. A failure here means a Phase 1 module has a bug that GUI code would otherwise silently build on top of.

- [ ] **Step 3: Commit a checkpoint marker**

```bash
git commit --allow-empty -m "Checkpoint: engine test suite green, starting GUI phase"
```

---

## Task 12: GUI entrypoint and empty MainWindow

**Files:**
- Create: `gui/__init__.py`
- Create: `gui/main.py`
- Create: `gui/main_window.py`
- Test: `tests/test_gui_smoke.py` (created here, extended in Task 21)

**Interfaces:**
- Consumes: `settings.AppSettings` (Task 9).
- Produces: `MainWindow(QMainWindow)` — constructible with no args, exposes `self.settings: AppSettings` and a `self.settings_path: Path` fixed at `Path.home() / ".cropper" / "settings.json"`. `gui/main.py` exposes `main() -> int` (creates `QApplication`, `MainWindow`, calls `app.exec()`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gui_smoke.py
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])


class MainWindowSmokeTests(unittest.TestCase):
    def test_main_window_constructs(self):
        from gui.main_window import MainWindow
        window = MainWindow()
        self.assertIsNotNone(window.settings)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.main_window'`.

- [ ] **Step 3: Write `gui/__init__.py`, `gui/main_window.py`, `gui/main.py`**

`gui/__init__.py`:
```python
```

`gui/main_window.py`:
```python
"""Main window: wired up incrementally through Tasks 13-21."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import QMainWindow

from settings import AppSettings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cropper")
        self.settings_path = Path.home() / ".cropper" / "settings.json"
        self.settings = AppSettings.load(self.settings_path)
```

`gui/main.py`:
```python
"""Cropper desktop app entrypoint. Run with: python gui/main.py"""
import sys

from PySide6.QtWidgets import QApplication

from main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1100, 750)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.path.insert(0, ".")
    sys.exit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gui/__init__.py gui/main.py gui/main_window.py tests/test_gui_smoke.py
git commit -m "Add GUI entrypoint and empty MainWindow"
```

---

## Task 13: Input panel (folder picker, drag-drop, shape/canvas/filter controls)

**Files:**
- Create: `gui/input_panel.py`
- Modify: `tests/test_gui_smoke.py` (append tests)

**Interfaces:**
- Consumes: `settings.AppSettings` (Task 9, for initial control values).
- Produces: `InputPanel(QWidget)` — constructor `InputPanel(initial_settings: AppSettings)`; attributes `folder_edit: QLineEdit`, `shape_combo: QComboBox` (items `square`, `portrait`, `landscape`), `canvas_spin: QSpinBox` (range 200–10000), `filter_checkbox: QCheckBox`; method `current_folder() -> str`; Qt signal `process_requested = Signal(str, str, int, bool)` emitted as `(folder, shape, canvas_long, apply_filter)` when the "Process Folder" button is clicked; supports drag-and-drop of a single folder onto the widget (sets `folder_edit` text).

- [ ] **Step 1: Write the failing tests (appended to `tests/test_gui_smoke.py`)**

Append:

```python
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtCore import QPoint

from gui.input_panel import InputPanel  # noqa: E402
from settings import AppSettings  # noqa: E402


class InputPanelTests(unittest.TestCase):
    def test_defaults_come_from_settings(self):
        panel = InputPanel(AppSettings(shape="portrait", canvas_long=1800, apply_filter=False))
        self.assertEqual(panel.shape_combo.currentText(), "portrait")
        self.assertEqual(panel.canvas_spin.value(), 1800)
        self.assertFalse(panel.filter_checkbox.isChecked())

    def test_process_requested_emits_current_values(self):
        panel = InputPanel(AppSettings())
        panel.folder_edit.setText("C:/photos")
        panel.shape_combo.setCurrentText("landscape")
        panel.canvas_spin.setValue(3000)
        panel.filter_checkbox.setChecked(False)

        received = []
        panel.process_requested.connect(lambda *args: received.append(args))
        panel._on_process_clicked()

        self.assertEqual(received, [("C:/photos", "landscape", 3000, False)])

    def test_current_folder_reflects_folder_edit(self):
        panel = InputPanel(AppSettings())
        panel.folder_edit.setText("C:/some/folder")
        self.assertEqual(panel.current_folder(), "C:/some/folder")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.input_panel'`.

- [ ] **Step 3: Write `gui/input_panel.py`**

```python
"""Input panel: folder picker, drag-and-drop, and per-run controls (shape,
canvas size, filter on/off). Emits process_requested when the user starts a run."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)


class InputPanel(QWidget):
    process_requested = Signal(str, str, int, bool)

    def __init__(self, initial_settings):
        super().__init__()
        self.setAcceptDrops(True)

        self.folder_edit = QLineEdit(initial_settings.last_input_folder)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._on_browse_clicked)

        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["square", "portrait", "landscape"])
        self.shape_combo.setCurrentText(initial_settings.shape)

        self.canvas_spin = QSpinBox()
        self.canvas_spin.setRange(200, 10000)
        self.canvas_spin.setValue(initial_settings.canvas_long)

        self.filter_checkbox = QCheckBox("Apply HP5 filter")
        self.filter_checkbox.setChecked(initial_settings.apply_filter)

        process_button = QPushButton("Process Folder")
        process_button.clicked.connect(self._on_process_clicked)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder:"))
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(browse_button)

        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel("Shape:"))
        controls_row.addWidget(self.shape_combo)
        controls_row.addWidget(QLabel("Canvas long edge:"))
        controls_row.addWidget(self.canvas_spin)
        controls_row.addWidget(self.filter_checkbox)
        controls_row.addWidget(process_button)

        layout = QVBoxLayout(self)
        layout.addLayout(folder_row)
        layout.addLayout(controls_row)

    def current_folder(self) -> str:
        return self.folder_edit.text()

    def _on_browse_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose input folder")
        if folder:
            self.folder_edit.setText(folder)

    def _on_process_clicked(self):
        self.process_requested.emit(
            self.folder_edit.text(),
            self.shape_combo.currentText(),
            self.canvas_spin.value(),
            self.filter_checkbox.isChecked(),
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.folder_edit.setText(urls[0].toLocalFile())
        event.acceptProposedAction()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: all tests so far PASS (1 from Task 12 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add gui/input_panel.py tests/test_gui_smoke.py
git commit -m "Add input panel: folder picker, drag-drop, shape/canvas/filter controls"
```

---

## Task 14: Background workers (QThread)

**Files:**
- Create: `gui/workers.py`
- Modify: `tests/test_gui_smoke.py` (append tests)

**Interfaces:**
- Consumes: `pipeline.process_folder`, `pipeline.apply_escalation`, `pipeline.PhotoJob` (Task 10).
- Produces: `ProcessFolderWorker(QThread)` — constructor `(folder: str, shape: str, canvas_long: int, apply_filter: bool)`, signals `photo_ready = Signal(object)` (emits `PhotoJob`), `finished_all = Signal()`. `EscalationWorker(QThread)` — constructor `(job: PhotoJob, provider, tier: str)`, signals `photo_updated = Signal(object)` (emits `PhotoJob`), `error = Signal(str)`.

- [ ] **Step 1: Write the failing tests (appended to `tests/test_gui_smoke.py`)**

Append:

```python
import tempfile
import time

import numpy as np
from PIL import Image

from gui.workers import EscalationWorker, ProcessFolderWorker  # noqa: E402
from providers.base import CropDecision  # noqa: E402
import pipeline as P  # noqa: E402


def _write_synthetic(path, seed=0):
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(200, 300, 3), dtype=np.uint8)
    Image.fromarray(arr).save(path, quality=95)


class ProcessFolderWorkerTests(unittest.TestCase):
    def test_worker_emits_one_signal_per_photo_then_finishes(self):
        with tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            _write_synthetic(os.path.join(d, "b.jpg"), seed=2)

            received = []
            worker = ProcessFolderWorker(d, "square", 600, True)
            worker.photo_ready.connect(lambda job: received.append(job))
            done = []
            worker.finished_all.connect(lambda: done.append(True))
            worker.start()
            worker.wait(10000)
            _app.processEvents()

            self.assertEqual(len(received), 2)
            self.assertEqual(done, [True])


class EscalationWorkerTests(unittest.TestCase):
    def test_worker_emits_updated_job_on_success(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            _write_synthetic(src)
            job = P.process_photo(src, "square", 600, True)

            class FakeProvider:
                def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
                    return CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=0.9, tier=tier)

            received = []
            worker = EscalationWorker(job, FakeProvider(), "strong")
            worker.photo_updated.connect(lambda j: received.append(j))
            worker.start()
            worker.wait(10000)
            _app.processEvents()

            self.assertEqual(len(received), 1)
            self.assertEqual(received[0].crop_decision.tier, "strong")

    def test_worker_emits_error_signal_on_failure(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "a.jpg")
            _write_synthetic(src)
            job = P.process_photo(src, "square", 600, True)

            class FailingProvider:
                def request_crop(self, *a, **kw):
                    raise RuntimeError("api down")

            errors = []
            worker = EscalationWorker(job, FailingProvider(), "cheap")
            worker.error.connect(lambda msg: errors.append(msg))
            worker.start()
            worker.wait(10000)
            _app.processEvents()

            self.assertEqual(errors, ["api down"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.workers'`.

- [ ] **Step 3: Write `gui/workers.py`**

```python
"""QThread workers wrapping pipeline calls so the GUI event loop never blocks
on image processing or a network call."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import QThread, Signal

import pipeline as P


class ProcessFolderWorker(QThread):
    photo_ready = Signal(object)
    finished_all = Signal()

    def __init__(self, folder, shape, canvas_long, apply_filter):
        super().__init__()
        self.folder = folder
        self.shape = shape
        self.canvas_long = canvas_long
        self.apply_filter = apply_filter

    def run(self):
        for job in P.process_folder(self.folder, self.shape, self.canvas_long, self.apply_filter):
            self.photo_ready.emit(job)
        self.finished_all.emit()


class EscalationWorker(QThread):
    photo_updated = Signal(object)
    error = Signal(str)

    def __init__(self, job, provider, tier):
        super().__init__()
        self.job = job
        self.provider = provider
        self.tier = tier

    def run(self):
        try:
            updated = P.apply_escalation(self.job, self.provider, self.tier)
            self.photo_updated.emit(updated)
        except Exception as e:  # noqa: BLE001 - surfaced to the GUI via the error signal
            self.error.emit(str(e))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: all tests so far PASS (4 from Tasks 12–13 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add gui/workers.py tests/test_gui_smoke.py
git commit -m "Add background QThread workers for folder processing and escalation"
```

---

## Task 15: Review gallery (thumbnail grid, keep/discard)

**Files:**
- Create: `gui/review_gallery.py`
- Modify: `tests/test_gui_smoke.py` (append tests)

**Interfaces:**
- Consumes: `pipeline.PhotoJob` (Task 10).
- Produces: `PhotoCard(QWidget)` — constructor `(job: PhotoJob)`, attributes `job: PhotoJob`, `keep_checkbox: QCheckBox`; signals `escalate_requested = Signal(object)` (emits the `PhotoJob`), `manual_crop_requested = Signal(object)`, `details_requested = Signal(object)`; method `update_job(job: PhotoJob) -> None` (refreshes thumbnail/state after escalation or manual crop). `ReviewGallery(QWidget)` — method `add_job(job: PhotoJob) -> None` (creates and lays out a `PhotoCard`), `update_job(job: PhotoJob) -> None` (finds the existing card for `job.src_path` and calls its `update_job`), `kept_jobs() -> list[PhotoJob]` (returns jobs whose card's `keep_checkbox` is checked); attribute `cards: dict[str, PhotoCard]` keyed by `job.src_path`.

- [ ] **Step 1: Write the failing tests (appended to `tests/test_gui_smoke.py`)**

Append:

```python
from gui.review_gallery import PhotoCard, ReviewGallery  # noqa: E402


def _make_job(name="a.jpg", keep=False):
    job = P.PhotoJob(src_path=f"/tmp/{name}", filename=name, shape="square",
                      canvas_long=600, apply_filter=True)
    job.rendered = Image.new("L", (600, 600), 128)
    job.keep = keep
    return job


class PhotoCardTests(unittest.TestCase):
    def test_card_holds_job_and_keep_checkbox_defaults_unchecked(self):
        card = PhotoCard(_make_job())
        self.assertFalse(card.keep_checkbox.isChecked())

    def test_toggling_checkbox_updates_job_keep_flag(self):
        card = PhotoCard(_make_job())
        card.keep_checkbox.setChecked(True)
        self.assertTrue(card.job.keep)

    def test_escalate_button_emits_signal_with_job(self):
        job = _make_job()
        card = PhotoCard(job)
        received = []
        card.escalate_requested.connect(lambda j: received.append(j))
        card._on_escalate_clicked()
        self.assertEqual(received, [job])


class ReviewGalleryTests(unittest.TestCase):
    def test_add_job_creates_a_card(self):
        gallery = ReviewGallery()
        job = _make_job("a.jpg")
        gallery.add_job(job)
        self.assertIn(job.src_path, gallery.cards)

    def test_kept_jobs_returns_only_checked_ones(self):
        gallery = ReviewGallery()
        job_a, job_b = _make_job("a.jpg"), _make_job("b.jpg")
        gallery.add_job(job_a)
        gallery.add_job(job_b)
        gallery.cards[job_a.src_path].keep_checkbox.setChecked(True)
        kept = gallery.kept_jobs()
        self.assertEqual(kept, [job_a])

    def test_update_job_refreshes_existing_card(self):
        gallery = ReviewGallery()
        job = _make_job("a.jpg")
        gallery.add_job(job)
        job.rendered = Image.new("L", (600, 600), 200)
        gallery.update_job(job)
        self.assertIs(gallery.cards[job.src_path].job, job)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.review_gallery'`.

- [ ] **Step 3: Write `gui/review_gallery.py`**

```python
"""Review gallery: one card per photo, keep/discard checkbox, and entry points
into escalation, manual crop, and the detection detail view."""
from PySide6.QtCore import Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)


def _pil_to_pixmap(pil_image, max_size=220):
    thumb = pil_image.copy()
    thumb.thumbnail((max_size, max_size))
    thumb = thumb.convert("RGB")
    qimage = QImage(thumb.tobytes(), thumb.width, thumb.height,
                     thumb.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage)


class PhotoCard(QWidget):
    escalate_requested = Signal(object)
    manual_crop_requested = Signal(object)
    details_requested = Signal(object)

    def __init__(self, job):
        super().__init__()
        self.job = job

        self.thumb_label = QLabel()
        self.status_label = QLabel()
        self.keep_checkbox = QCheckBox("Keep")
        self.keep_checkbox.toggled.connect(self._on_keep_toggled)

        escalate_button = QPushButton("Escalate")
        escalate_button.setEnabled(bool(job.triage_decision and job.triage_decision.escalate))
        escalate_button.clicked.connect(self._on_escalate_clicked)

        crop_button = QPushButton("Manual Crop")
        crop_button.clicked.connect(lambda: self.manual_crop_requested.emit(self.job))

        details_button = QPushButton("Details")
        details_button.clicked.connect(lambda: self.details_requested.emit(self.job))

        layout = QVBoxLayout(self)
        layout.addWidget(self.thumb_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.keep_checkbox)
        layout.addWidget(escalate_button)
        layout.addWidget(crop_button)
        layout.addWidget(details_button)

        self._refresh_visuals()

    def _on_keep_toggled(self, checked):
        self.job.keep = checked

    def _on_escalate_clicked(self):
        self.escalate_requested.emit(self.job)

    def update_job(self, job):
        self.job = job
        self._refresh_visuals()

    def _refresh_visuals(self):
        if self.job.error:
            self.status_label.setText(f"FAILED: {self.job.error}")
            return
        if self.job.rendered is not None:
            self.thumb_label.setPixmap(_pil_to_pixmap(self.job.rendered))
        if self.job.crop_decision is not None:
            self.status_label.setText(
                f"escalated ({self.job.crop_decision.tier}, "
                f"confidence {self.job.crop_decision.confidence:.2f})"
            )
        elif self.job.triage_decision and self.job.triage_decision.escalate:
            self.status_label.setText("flagged for escalation")
        else:
            self.status_label.setText("formula crop")


class ReviewGallery(QScrollArea):
    def __init__(self):
        super().__init__()
        self.cards = {}
        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self._next_index = 0

    def add_job(self, job):
        card = PhotoCard(job)
        self.cards[job.src_path] = card
        row, col = divmod(self._next_index, 4)
        self._grid.addWidget(card, row, col)
        self._next_index += 1

    def update_job(self, job):
        card = self.cards.get(job.src_path)
        if card is not None:
            card.update_job(job)

    def kept_jobs(self):
        return [card.job for card in self.cards.values() if card.keep_checkbox.isChecked()]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: all tests so far PASS (7 from Tasks 12–14 + 6 new).

- [ ] **Step 5: Commit**

```bash
git add gui/review_gallery.py tests/test_gui_smoke.py
git commit -m "Add review gallery: photo cards, keep/discard, escalate/crop/details entry points"
```

---

## Task 16: Detail view dialog (detection overlay, confidence/tier)

**Files:**
- Create: `gui/detail_view_dialog.py`
- Modify: `tests/test_gui_smoke.py` (append tests)

**Interfaces:**
- Consumes: `pipeline.PhotoJob` (Task 10).
- Produces: `render_detection_overlay(job: PhotoJob) -> PIL.Image` (draws face boxes on a copy of `job.rendered`-sized preview; pure function, independently testable), `DetailViewDialog(QDialog)` — constructor `(job: PhotoJob, parent=None)`.

- [ ] **Step 1: Write the failing tests (appended to `tests/test_gui_smoke.py`)**

Append:

```python
from gui.detail_view_dialog import DetailViewDialog, render_detection_overlay  # noqa: E402
from detection import DetectionResult, FaceBox, SaliencyResult  # noqa: E402


class DetectionOverlayTests(unittest.TestCase):
    def test_overlay_is_same_size_as_source_and_marks_a_face(self):
        job = _make_job("a.jpg")
        job.detection = DetectionResult(
            faces=[FaceBox(10, 10, 40, 40)],
            saliency=SaliencyResult(heatmap=np.zeros((600, 600), dtype="float32"),
                                     blob_fraction=0.2, touches_edge=False),
            symmetry_score=0.9,
        )
        overlay = render_detection_overlay(job)
        self.assertEqual(overlay.size, job.rendered.size)
        # a pixel on the drawn face-box border should differ from plain mid-gray background
        overlay_arr = np.asarray(overlay.convert("RGB"))
        self.assertFalse((overlay_arr[10, 10:50] == overlay_arr[10, 10, 0]).all())


class DetailViewDialogTests(unittest.TestCase):
    def test_dialog_constructs_with_job(self):
        job = _make_job("a.jpg")
        job.detection = DetectionResult(
            faces=[], saliency=SaliencyResult(heatmap=np.zeros((10, 10), dtype="float32"),
                                               blob_fraction=0.0, touches_edge=False),
            symmetry_score=0.5,
        )
        dialog = DetailViewDialog(job)
        self.assertIsNotNone(dialog)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.detail_view_dialog'`.

- [ ] **Step 3: Write `gui/detail_view_dialog.py`**

```python
"""Per-photo detail view: what the detection pass found (face boxes, saliency
blob, symmetry score) and, if escalated, the AI's confidence and tier. Not
shown in the main gallery grid by default - opened on demand from a card's
Details button."""
from PIL import ImageDraw

from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout


def render_detection_overlay(job):
    base = job.rendered.convert("RGB").copy()
    draw = ImageDraw.Draw(base)
    if job.detection is not None:
        scale_x = base.width / (job.detection.saliency.heatmap.shape[1] or base.width)
        scale_y = base.height / (job.detection.saliency.heatmap.shape[0] or base.height)
        for face in job.detection.faces:
            x0, y0 = face.x * scale_x, face.y * scale_y
            x1, y1 = (face.x + face.w) * scale_x, (face.y + face.h) * scale_y
            draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=3)
    return base


class DetailViewDialog(QDialog):
    def __init__(self, job, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Details - {job.filename}")
        overlay = render_detection_overlay(job)
        rgb = overlay.tobytes()
        qimage = QImage(rgb, overlay.width, overlay.height,
                         overlay.width * 3, QImage.Format.Format_RGB888)

        image_label = QLabel()
        image_label.setPixmap(QPixmap.fromImage(qimage))

        info_lines = []
        if job.detection is not None:
            info_lines.append(f"Faces detected: {len(job.detection.faces)}")
            info_lines.append(f"Saliency blob fraction: {job.detection.saliency.blob_fraction:.2f}")
            info_lines.append(f"Symmetry score: {job.detection.symmetry_score:.2f}")
        if job.triage_decision is not None:
            info_lines.append(f"Escalation reasons: {', '.join(job.triage_decision.reasons) or 'none'}")
        if job.crop_decision is not None:
            info_lines.append(
                f"AI decision: tier={job.crop_decision.tier}, "
                f"confidence={job.crop_decision.confidence:.2f}"
            )
        info_label = QLabel("\n".join(info_lines))

        layout = QVBoxLayout(self)
        layout.addWidget(image_label)
        layout.addWidget(info_label)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: all tests so far PASS (13 from Tasks 12–15 + 2 new).

- [ ] **Step 5: Commit**

```bash
git add gui/detail_view_dialog.py tests/test_gui_smoke.py
git commit -m "Add detection detail view dialog with face-box overlay"
```

---

## Task 17: Manual crop editor (interactive, ratio-locked)

**Files:**
- Create: `gui/crop_editor_dialog.py`
- Test: `tests/test_crop_editor_state.py`
- Modify: `tests/test_gui_smoke.py` (append one construction test)

**Interfaces:**
- Consumes: `crop.CropBox` (Task 4).
- Produces: `CropBoxState(img_w: int, img_h: int, ratio: float, x: float, y: float, w: float)` (dataclass; `.h` property derived from `ratio`; `.move_by(dx, dy) -> None`; `.resize_to(new_w: float) -> None`; `.to_crop_box() -> crop.CropBox`), `CropEditorDialog(QDialog)` — constructor `(job: PhotoJob, inner_ratio: float, parent=None)`, method `result_crop_box() -> crop.CropBox | None` (returns `None` if the dialog was cancelled).

`CropBoxState` is pure math with no Qt dependency, so it gets its own plain-`unittest` test file (no `QApplication` needed); `CropEditorDialog` wraps it in a paint/mouse-event widget and gets one construction smoke test in `tests/test_gui_smoke.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_crop_editor_state.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gui.crop_editor_dialog import CropBoxState  # noqa: E402


class CropBoxStateTests(unittest.TestCase):
    def test_h_derived_from_ratio(self):
        state = CropBoxState(img_w=1000, img_h=800, ratio=2.0, x=0, y=0, w=400)
        self.assertEqual(state.h, 200)

    def test_move_by_clamps_to_image_bounds(self):
        state = CropBoxState(img_w=1000, img_h=800, ratio=1.0, x=0, y=0, w=200)
        state.move_by(-50, -50)
        self.assertEqual((state.x, state.y), (0, 0))
        state.move_by(10000, 10000)
        self.assertEqual(state.x, 1000 - 200)
        self.assertEqual(state.y, 800 - 200)

    def test_resize_to_keeps_ratio_and_clamps_to_shorter_dimension(self):
        state = CropBoxState(img_w=1000, img_h=800, ratio=2.0, x=0, y=0, w=400)
        state.resize_to(2000)
        # height would be 2000/2=1000 > img_h=800, so it must clamp on height instead
        self.assertLessEqual(state.h, 800)
        self.assertAlmostEqual(state.w / state.h, 2.0, places=3)

    def test_resize_to_repositions_box_if_it_would_overflow(self):
        state = CropBoxState(img_w=1000, img_h=800, ratio=1.0, x=900, y=0, w=100)
        state.resize_to(300)
        self.assertLessEqual(state.x + state.w, 1000)

    def test_to_crop_box_returns_fractions(self):
        state = CropBoxState(img_w=1000, img_h=800, ratio=1.0, x=100, y=100, w=200)
        box = state.to_crop_box()
        self.assertAlmostEqual(box.x0, 0.1)
        self.assertAlmostEqual(box.y0, 0.125)
        self.assertAlmostEqual(box.x1, 0.3)
        self.assertAlmostEqual(box.y1, 0.375)


if __name__ == "__main__":
    unittest.main()
```

Append to `tests/test_gui_smoke.py`:

```python
from gui.crop_editor_dialog import CropEditorDialog  # noqa: E402


class CropEditorDialogTests(unittest.TestCase):
    def test_dialog_constructs_and_starts_with_no_result(self):
        job = _make_job("a.jpg")
        dialog = CropEditorDialog(job, inner_ratio=1.0)
        self.assertIsNone(dialog.result_crop_box())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_crop_editor_state -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.crop_editor_dialog'`.

- [ ] **Step 3: Write `gui/crop_editor_dialog.py`**

```python
"""Interactive, ratio-locked manual crop override. CropBoxState holds the pure
coordinate math (independently testable); CropEditorDialog wraps it with mouse
drag/resize handling and painting."""
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PIL import ImageQt
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget

from crop import CropBox


@dataclass
class CropBoxState:
    img_w: int
    img_h: int
    ratio: float
    x: float
    y: float
    w: float

    @property
    def h(self) -> float:
        return self.w / self.ratio

    def move_by(self, dx: float, dy: float) -> None:
        self.x = max(0, min(self.x + dx, self.img_w - self.w))
        self.y = max(0, min(self.y + dy, self.img_h - self.h))

    def resize_to(self, new_w: float) -> None:
        new_w = max(10.0, min(new_w, float(self.img_w)))
        new_h = new_w / self.ratio
        if new_h > self.img_h:
            new_h = float(self.img_h)
            new_w = new_h * self.ratio
        self.w = new_w
        self.x = min(self.x, self.img_w - self.w)
        self.y = min(self.y, self.img_h - self.h)

    def to_crop_box(self) -> CropBox:
        return CropBox(
            x0=self.x / self.img_w, y0=self.y / self.img_h,
            x1=(self.x + self.w) / self.img_w, y1=(self.y + self.h) / self.img_h,
        )


class _CropCanvas(QWidget):
    def __init__(self, pil_image, state: CropBoxState):
        super().__init__()
        self.pixmap = QPixmap.fromImage(ImageQt.ImageQt(pil_image.convert("RGB")))
        self.state = state
        self.setFixedSize(self.pixmap.size())
        self._dragging = False
        self._last_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        pen = QPen(Qt.GlobalColor.red)
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawRect(QRect(int(self.state.x), int(self.state.y),
                                int(self.state.w), int(self.state.h)))

    def mousePressEvent(self, event):
        self._dragging = True
        self._last_pos = event.position()

    def mouseMoveEvent(self, event):
        if self._dragging and self._last_pos is not None:
            delta = event.position() - self._last_pos
            self.state.move_by(delta.x(), delta.y())
            self._last_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def wheelEvent(self, event):
        step = 20 if event.angleDelta().y() > 0 else -20
        self.state.resize_to(self.state.w + step)
        self.update()


class CropEditorDialog(QDialog):
    def __init__(self, job, inner_ratio: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Manual crop - {job.filename}")
        img = job.rendered.convert("RGB")
        start_w = min(img.width, round(img.height * inner_ratio))
        self.state = CropBoxState(
            img_w=img.width, img_h=img.height, ratio=inner_ratio,
            x=(img.width - start_w) / 2, y=0, w=start_w,
        )
        self._canvas = _CropCanvas(img, self.state)
        self._accepted = False

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._canvas)
        layout.addWidget(buttons)

    def _on_accept(self):
        self._accepted = True
        self.accept()

    def result_crop_box(self):
        if not self._accepted:
            return None
        return self.state.to_crop_box()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_crop_editor_state -v`
Expected: all 5 tests PASS.

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: all tests so far PASS (15 from Tasks 12–16 + 1 new).

- [ ] **Step 5: Commit**

```bash
git add gui/crop_editor_dialog.py tests/test_crop_editor_state.py tests/test_gui_smoke.py
git commit -m "Add interactive ratio-locked manual crop editor"
```

---

## Task 18: Escalation confirmation dialog (cost estimate gate)

**Files:**
- Create: `gui/escalation_dialog.py`
- Modify: `tests/test_gui_smoke.py` (append tests)

**Interfaces:**
- Consumes: `cost.estimate_worst_case_batch_cost` (Task 7), `providers.base.CropProvider` (Task 5).
- Produces: `EscalationConfirmDialog(QDialog)` — constructor `(provider, num_photos: int, parent=None)`; shows the worst-case dollar estimate via `cost.estimate_worst_case_batch_cost(provider, num_photos)`; method `confirmed() -> bool` (`True` only if the user clicked "Escalate", `False` on cancel or if never shown/accepted).

- [ ] **Step 1: Write the failing tests (appended to `tests/test_gui_smoke.py`)**

Append:

```python
from gui.escalation_dialog import EscalationConfirmDialog  # noqa: E402


class EscalationConfirmDialogTests(unittest.TestCase):
    def test_shows_worst_case_cost_and_defaults_unconfirmed(self):
        class FakeProvider:
            def price_per_million_tokens(self, tier):
                return (10.0, 50.0)

        dialog = EscalationConfirmDialog(FakeProvider(), num_photos=3)
        self.assertFalse(dialog.confirmed())
        self.assertIn("$", dialog.cost_label.text())

    def test_accept_marks_confirmed(self):
        class FakeProvider:
            def price_per_million_tokens(self, tier):
                return (10.0, 50.0)

        dialog = EscalationConfirmDialog(FakeProvider(), num_photos=1)
        dialog._on_accept()
        self.assertTrue(dialog.confirmed())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.escalation_dialog'`.

- [ ] **Step 3: Write `gui/escalation_dialog.py`**

```python
"""Confirmation gate shown before any paid escalation call: a worst-case cost
estimate (every flagged photo assumed to need the strong tier), approved
explicitly before spend happens."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import QDialogButtonBox, QLabel, QVBoxLayout, QDialog

from cost import estimate_worst_case_batch_cost


class EscalationConfirmDialog(QDialog):
    def __init__(self, provider, num_photos: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm AI escalation")
        self._confirmed = False

        worst_case = estimate_worst_case_batch_cost(provider, num_photos)
        self.cost_label = QLabel(
            f"Escalating {num_photos} photo(s) could cost up to ${worst_case:.4f} "
            "(worst case, assumes every photo needs the stronger tier)."
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Escalate")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.cost_label)
        layout.addWidget(buttons)

    def _on_accept(self):
        self._confirmed = True
        self.accept()

    def confirmed(self) -> bool:
        return self._confirmed
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: all tests so far PASS (16 from Tasks 12–17 + 2 new).

- [ ] **Step 5: Commit**

```bash
git add gui/escalation_dialog.py tests/test_gui_smoke.py
git commit -m "Add escalation cost-estimate confirmation dialog"
```

---

## Task 19: Cost panel (running total + decision history)

**Files:**
- Create: `gui/cost_panel.py`
- Modify: `tests/test_gui_smoke.py` (append tests)

**Interfaces:**
- Consumes: `decision_log.DecisionLog`, `decision_log.DecisionRecord` (Task 8).
- Produces: `CostPanel(QWidget)` — constructor `(decision_log: DecisionLog)`; method `refresh() -> None` (re-reads `decision_log.records` / `.running_cost` and updates the display); attributes `total_label: QLabel`, `history_list: QListWidget`.

- [ ] **Step 1: Write the failing tests (appended to `tests/test_gui_smoke.py`)**

Append:

```python
import tempfile
from pathlib import Path as _Path

from gui.cost_panel import CostPanel  # noqa: E402
import decision_log as DL  # noqa: E402


class CostPanelTests(unittest.TestCase):
    def test_refresh_shows_running_total_and_history_rows(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(_Path(d) / "log.jsonl")
            log.add(DL.DecisionRecord(photo_name="a.jpg", escalated=True, tier="cheap",
                                       provider="openai", cost=0.001, confidence=0.9,
                                       timestamp=1.0))
            panel = CostPanel(log)
            panel.refresh()
            self.assertIn("0.001", panel.total_label.text())
            self.assertEqual(panel.history_list.count(), 1)

    def test_refresh_after_new_record_updates_total(self):
        with tempfile.TemporaryDirectory() as d:
            log = DL.DecisionLog(_Path(d) / "log.jsonl")
            panel = CostPanel(log)
            panel.refresh()
            log.add(DL.DecisionRecord(photo_name="b.jpg", escalated=True, tier="strong",
                                       provider="openai", cost=0.05, confidence=0.3,
                                       timestamp=2.0))
            panel.refresh()
            self.assertIn("0.05", panel.total_label.text())
            self.assertEqual(panel.history_list.count(), 1)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.cost_panel'`.

- [ ] **Step 3: Write `gui/cost_panel.py`**

```python
"""Running cost total and per-photo decision history, visible in-app rather
than only in the background log file."""
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget


class CostPanel(QWidget):
    def __init__(self, decision_log):
        super().__init__()
        self.decision_log = decision_log
        self.total_label = QLabel("Running cost: $0.000000")
        self.history_list = QListWidget()

        layout = QVBoxLayout(self)
        layout.addWidget(self.total_label)
        layout.addWidget(self.history_list)

        self.refresh()

    def refresh(self) -> None:
        self.total_label.setText(f"Running cost: ${self.decision_log.running_cost:.6f}")
        self.history_list.clear()
        for record in self.decision_log.records:
            if record.escalated:
                text = (f"{record.photo_name}: {record.provider}/{record.tier}, "
                        f"confidence {record.confidence:.2f}, ${record.cost:.6f}")
            else:
                text = f"{record.photo_name}: not escalated"
            self.history_list.addItem(text)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: all tests so far PASS (18 from Tasks 12–18 + 2 new).

- [ ] **Step 5: Commit**

```bash
git add gui/cost_panel.py tests/test_gui_smoke.py
git commit -m "Add cost panel: running total and decision history"
```

---

## Task 20: Save action

**Files:**
- Create: `gui/save_action.py`
- Modify: `tests/test_gui_smoke.py` (append tests)

**Interfaces:**
- Consumes: `pipeline.PhotoJob` (Task 10).
- Produces: `save_kept_jobs(jobs: list[PhotoJob], output_folder: str) -> list[str]` (writes each kept job's `.rendered` image to `<output_folder>/<stem>_cropper.jpg`, creates the folder if missing, returns the list of written paths; skips jobs with `job.error` set even if `keep` is `True`).

- [ ] **Step 1: Write the failing tests (appended to `tests/test_gui_smoke.py`)**

Append:

```python
from gui.save_action import save_kept_jobs  # noqa: E402


class SaveActionTests(unittest.TestCase):
    def test_saves_only_kept_jobs_to_output_folder(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = os.path.join(d, "out")
            job_a = _make_job("a.jpg", keep=True)
            job_b = _make_job("b.jpg", keep=False)
            written = save_kept_jobs([job_a, job_b], out_dir)
            self.assertEqual(len(written), 1)
            self.assertTrue(os.path.exists(written[0]))
            self.assertIn("a", os.path.basename(written[0]))

    def test_skips_jobs_with_errors_even_if_marked_keep(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = os.path.join(d, "out")
            job = _make_job("a.jpg", keep=True)
            job.error = "boom"
            written = save_kept_jobs([job], out_dir)
            self.assertEqual(written, [])

    def test_creates_output_folder_if_missing(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = os.path.join(d, "does", "not", "exist", "yet")
            job = _make_job("a.jpg", keep=True)
            save_kept_jobs([job], out_dir)
            self.assertTrue(os.path.isdir(out_dir))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gui.save_action'`.

- [ ] **Step 3: Write `gui/save_action.py`**

```python
"""Explicit save: writes only the jobs the user marked to keep, to the
chosen output folder. Nothing else in the app ever writes to disk."""
import os


def save_kept_jobs(jobs, output_folder: str) -> list:
    os.makedirs(output_folder, exist_ok=True)
    written = []
    for job in jobs:
        if not job.keep or job.error or job.rendered is None:
            continue
        stem = os.path.splitext(job.filename)[0]
        dst = os.path.join(output_folder, f"{stem}_cropper.jpg")
        job.rendered.convert("L").save(dst, quality=92, optimize=True)
        written.append(dst)
    return written
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: all tests so far PASS (20 from Tasks 12–19 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add gui/save_action.py tests/test_gui_smoke.py
git commit -m "Add explicit save action for kept photos"
```

---

## Task 21: Wire everything together in MainWindow

**Files:**
- Modify: `gui/main_window.py`
- Modify: `tests/test_gui_smoke.py` (append tests)

**Interfaces:**
- Consumes: everything from Tasks 9, 10, 12–20.
- Produces: `MainWindow` gains attributes `input_panel: InputPanel`, `gallery: ReviewGallery`, `cost_panel: CostPanel`, `decision_log: DecisionLog`, `provider: OpenAICropProvider`, `save_button: QPushButton`; method `output_folder() -> str` (returns `input_panel.current_folder() + "/out"` unless overridden — kept simple per the spec's fixed-default-with-override behavior, override wiring is a `QFileDialog` on a "Choose output folder..." button next to `save_button`); method `_run_escalation_worker(job, tier) -> None` (dispatches one `EscalationWorker` call at the given tier); module constant `AUTO_ESCALATE_CONFIDENCE_THRESHOLD: float` (0.6) driving the fully-automatic cheap→strong escalation in `_on_escalation_done` (Global Constraints: tier selection is automatic, no manual override).

- [ ] **Step 1: Write the failing tests (appended to `tests/test_gui_smoke.py`)**

Append:

```python
class MainWindowWiringTests(unittest.TestCase):
    def test_default_output_folder_is_input_folder_slash_out(self):
        from gui.main_window import MainWindow
        window = MainWindow()
        window.input_panel.folder_edit.setText("/tmp/photos")
        self.assertEqual(window.output_folder(), "/tmp/photos/out")

    def test_processing_a_folder_populates_the_gallery(self):
        from gui.main_window import MainWindow
        with tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = MainWindow()
            window.input_panel.folder_edit.setText(d)
            window.input_panel.shape_combo.setCurrentText("square")
            window.input_panel.canvas_spin.setValue(600)
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            self.assertEqual(len(window.gallery.cards), 1)

    def test_save_writes_only_kept_jobs(self):
        from gui.main_window import MainWindow
        with tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = MainWindow()
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            list(window.gallery.cards.values())[0].keep_checkbox.setChecked(True)
            window._on_save_clicked()
            out_dir = os.path.join(d, "out")
            self.assertTrue(os.path.isdir(out_dir))
            self.assertEqual(len(os.listdir(out_dir)), 1)

    def test_low_confidence_cheap_tier_automatically_escalates_to_strong(self):
        from gui.main_window import MainWindow
        with tempfile.TemporaryDirectory() as d:
            _write_synthetic(os.path.join(d, "a.jpg"), seed=1)
            window = MainWindow()
            window._start_processing(d, "square", 600, True)
            window._worker.wait(10000)
            _app.processEvents()
            job = list(window.gallery.cards.values())[0].job

            calls = []

            class FakeProvider:
                name = "openai"

                def price_per_million_tokens(self, tier):
                    return (1.0, 1.0)

                def request_crop(self, image_bytes, detection_metadata, inner_ratio, tier):
                    calls.append(tier)
                    confidence = 0.3 if tier == "cheap" else 0.95
                    return CropDecision(crop_box=(0.0, 0.0, 1.0, 1.0), confidence=confidence, tier=tier)

            window.provider = FakeProvider()
            window._run_escalation_worker(job, "cheap")
            self.assertEqual(calls, ["cheap", "strong"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: FAIL — `AttributeError: 'MainWindow' object has no attribute 'input_panel'` (or similar).

- [ ] **Step 3: Rewrite `gui/main_window.py`**

```python
"""Main window: wires the input panel, background workers, review gallery,
escalation flow, cost panel, and save action together."""
import sys
from pathlib import Path

# Two path inserts: "src" for the engine modules below, and this file's own
# directory (gui/) so the bare sibling imports below (cost_panel,
# crop_editor_dialog, etc.) resolve even when this module is loaded as
# gui.main_window (e.g. from tests) rather than run as a top-level script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from settings import AppSettings
from decision_log import DecisionLog, DecisionRecord
from providers.openai_provider import OpenAICropProvider
import pipeline as P

from cost_panel import CostPanel
from crop_editor_dialog import CropEditorDialog
from detail_view_dialog import DetailViewDialog
from escalation_dialog import EscalationConfirmDialog
from input_panel import InputPanel
from review_gallery import ReviewGallery
from save_action import save_kept_jobs
from workers import EscalationWorker, ProcessFolderWorker

# Below this confidence, the cheap-tier result auto-escalates to the strong
# tier. Fully automatic per the Global Constraints - no manual override.
AUTO_ESCALATE_CONFIDENCE_THRESHOLD = 0.6


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cropper")

        self.settings_path = Path.home() / ".cropper" / "settings.json"
        self.settings = AppSettings.load(self.settings_path)

        self.decision_log_path = Path.home() / ".cropper" / "decision_log.jsonl"
        self.decision_log = DecisionLog(self.decision_log_path)

        self.provider = OpenAICropProvider()
        self._output_override = None
        self._worker = None

        self.input_panel = InputPanel(self.settings)
        self.input_panel.process_requested.connect(self._start_processing)

        self.gallery = ReviewGallery()

        self.cost_panel = CostPanel(self.decision_log)

        self.save_button = QPushButton("Save Selected")
        self.save_button.clicked.connect(self._on_save_clicked)
        choose_output_button = QPushButton("Choose output folder...")
        choose_output_button.clicked.connect(self._on_choose_output_clicked)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.save_button)
        bottom_row.addWidget(choose_output_button)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.input_panel)
        layout.addWidget(self.gallery)
        layout.addWidget(self.cost_panel)
        layout.addLayout(bottom_row)
        self.setCentralWidget(central)

    def output_folder(self) -> str:
        if self._output_override:
            return self._output_override
        return self.input_panel.current_folder().rstrip("/\\") + "/out"

    def _on_choose_output_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if folder:
            self._output_override = folder

    def _start_processing(self, folder, shape, canvas_long, apply_filter):
        self.settings.shape = shape
        self.settings.canvas_long = canvas_long
        self.settings.apply_filter = apply_filter
        self.settings.last_input_folder = folder
        self.settings.save(self.settings_path)

        self._worker = ProcessFolderWorker(folder, shape, canvas_long, apply_filter)
        self._worker.photo_ready.connect(self._on_photo_ready)
        self._worker.start()

    def _on_photo_ready(self, job):
        self.gallery.add_job(job)
        card = self.gallery.cards[job.src_path]
        card.escalate_requested.connect(self._on_escalate_requested)
        card.manual_crop_requested.connect(self._on_manual_crop_requested)
        card.details_requested.connect(self._on_details_requested)

    def _on_escalate_requested(self, job):
        confirm = EscalationConfirmDialog(self.provider, num_photos=1, parent=self)
        confirm.exec()
        if not confirm.confirmed():
            return
        self._run_escalation_worker(job, "cheap")

    def _run_escalation_worker(self, job, tier):
        escalation_worker = EscalationWorker(job, self.provider, tier)
        escalation_worker.photo_updated.connect(self._on_escalation_done)
        escalation_worker.error.connect(
            lambda msg: QMessageBox.warning(self, "Escalation failed", msg)
        )
        escalation_worker.start()
        escalation_worker.wait()

    def _on_escalation_done(self, job):
        self.gallery.update_job(job)
        from cost import estimate_call_cost
        actual_cost = estimate_call_cost(self.provider, job.crop_decision.tier)
        self.decision_log.add(DecisionRecord(
            photo_name=job.filename, escalated=True, tier=job.crop_decision.tier,
            provider=self.provider.name, cost=actual_cost,
            confidence=job.crop_decision.confidence, timestamp=0.0,
        ))
        self.cost_panel.refresh()
        # Fully automatic tier escalation, no manual override (Global Constraints):
        # cheap tier first, escalate to strong only if confidence came back low.
        if job.crop_decision.tier == "cheap" and job.crop_decision.confidence < AUTO_ESCALATE_CONFIDENCE_THRESHOLD:
            self._run_escalation_worker(job, "strong")

    def _on_manual_crop_requested(self, job):
        lay_ratio = job.crop_box.x1 - job.crop_box.x0  # placeholder ratio if crop_box exists
        inner_ratio = (job.crop_box.x1 - job.crop_box.x0) / (job.crop_box.y1 - job.crop_box.y0) \
            if job.crop_box else 1.0
        dialog = CropEditorDialog(job, inner_ratio=inner_ratio, parent=self)
        dialog.exec()
        new_box = dialog.result_crop_box()
        if new_box is not None:
            updated = P.apply_manual_crop(job, new_box)
            self.gallery.update_job(updated)

    def _on_details_requested(self, job):
        dialog = DetailViewDialog(job, parent=self)
        dialog.exec()

    def _on_save_clicked(self):
        kept = self.gallery.kept_jobs()
        out_folder = self.output_folder()
        self.settings.last_output_folder = out_folder
        self.settings.save(self.settings_path)
        save_kept_jobs(kept, out_folder)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke -v`
Expected: all tests PASS (23 from Tasks 12–20 + 4 new = 27 total in this file).

- [ ] **Step 5: Run the entire project test suite one final time**

Run: `QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v`
Expected: every test across every file passes (48 engine tests from Task 11 + 27 GUI tests + 5 crop-editor-state tests = 80 tests, 0 failures).

- [ ] **Step 6: Manual verification (not automatable — do this once by hand)**

Run: `python gui/main.py`
Set `OPENAI_API_KEY` in the environment first if you want to try the live Escalate button.
Checklist:
- Drag a folder of JPEGs onto the window, or use Browse; set shape/canvas; click "Process Folder" — thumbnails appear progressively.
- Click "Details" on a photo — face box overlay and detection numbers show.
- Click "Manual Crop" — drag the red box around, scroll to resize, OK updates the thumbnail.
- Click "Escalate" on a flagged photo — cost dialog appears before any API call fires.
- Check a few "Keep" boxes, click "Save Selected" — confirm only those files land in `<input>/out/`.
- Close and reopen the app — shape/canvas/filter/last folder are remembered.

- [ ] **Step 7: Commit**

```bash
git add gui/main_window.py tests/test_gui_smoke.py
git commit -m "Wire input panel, workers, gallery, escalation, cost panel, and save into MainWindow"
```

---

## Self-Review Notes

- **Spec coverage:** every decided section of `.scratch/desktop-tool/spec.md` maps to a task — tech stack/versions (Task 1 + Global Constraints), filter toggle (Task 10/13), processing/review/save model (Tasks 10, 14, 15, 20), manual crop override (Task 17), escalation + confidence/tier display (Tasks 6, 15, 16, 18), cost estimate worst-case (Tasks 7, 18), provider-agnostic + OpenAI first (Tasks 5, 6), API key via env var (Task 6, `OpenAI()` default client — no code needed for the env var path itself; the in-app `keyring` override field was **not** included as its own task since the spec marks it optional/"convenience" and the env var path fully satisfies the requirement — flagging this as a deliberate scope trim, not an oversight, since `keyring` is still pinned in `requirements.txt` for when that override is added), decision log visible in-app (Tasks 8, 19), triage thresholds in code (Task 3), input folder+drag-drop (Task 13), output folder default+override (Task 21), error handling skip-and-continue (Task 10's `process_folder`, Task 15's error display), detection transparency in detail view (Task 16), settings persistence (Tasks 9, 21), one shape per run (Task 13's single shape combo, no per-photo override), border locked (never exposed — Global Constraints), portrait filter deferred (not built, per Global Constraints).
- **Placeholder scan:** no TBD/TODO markers; every step has runnable code and a concrete expected test result.
- **Type consistency check:** `PhotoJob` fields introduced in Task 10 (`detection`, `triage_decision`, `crop_box`, `crop_decision`, `rendered`, `keep`, `error`) are used with the same names in Tasks 14, 15, 16, 17, 20, 21. `CropBox(x0,y0,x1,y1)` from Task 4 is used identically in Tasks 10, 17, 21. `CropDecision(crop_box, confidence, tier)` from Task 5 is used identically in Tasks 6, 10, 15, 16, 21. `DecisionRecord` fields from Task 8 match their usage in Task 21's `_on_escalation_done`.
- **Fixed during self-review:** Task 21's `_on_photo_ready` originally had a dead no-op branch (`if not job.escalated_logged if hasattr(...) else True: pass`) left over from an earlier draft. Removed — it did nothing and no test exercised it either way.
- **Fixed during pre-flight conflict scan (before dispatch):**
  1. Task 21's `main_window.py` imported its `gui/` siblings (`cost_panel`, `crop_editor_dialog`, `detail_view_dialog`, `escalation_dialog`, `input_panel`, `review_gallery`, `save_action`, `workers`) as bare top-level modules, but every test that exercises this file loads it via `from gui.main_window import MainWindow` — a path where only `src/` and the repo root reach `sys.path`, never `gui/` itself. Only running `python gui/main.py` directly would have made those imports resolve (via Python's script-directory insertion), so the plan's own specified tests would have failed against the plan's own specified code. Fixed by adding a second `sys.path.insert` for the file's own directory, matching the pattern other `gui/` modules already use for reaching `src/`.
  2. The Global Constraints promised fully-automatic cheap→strong tier escalation ("escalate to the stronger tier only if the first reports low confidence... no manual override"), but no task implemented it — Task 21's `_on_escalate_requested` hardcoded `tier = "cheap"` with no follow-up. Fixed by moving the tier decision into `_on_escalation_done` (where the async result naturally lands): a new `_run_escalation_worker(job, tier)` helper is called again with `"strong"` when the cheap tier's confidence falls below `AUTO_ESCALATE_CONFIDENCE_THRESHOLD` (0.6). This required no changes to Tasks 10 or 14 — `apply_escalation` and `EscalationWorker` stay single-tier primitives, exactly as already tested there. Added one new test to Task 21 verifying the auto-escalation call sequence.
- **Fixed during Task 4 execution (implementer flagged it, controller ruled and fixed the plan text):** Task 4's `test_off_center_face_pulls_crop_toward_a_third_line` originally used a 1000×1000 image with `inner_ratio=1.0` — a square crop of a square image is forced to exactly fill the image with zero slack on either axis, making an off-center crop mathematically impossible regardless of face position or implementation correctness. Fixed by making the test image rectangular (1500×1000) so the square crop retains 500px of horizontal slack to actually shift.
