# MoodPortrait filter

Status: spec only, not started. Only D4 (UI placement) is open and deferred; it blocks only the UI part of ticket 05. Implement in a fresh session
(see CLAUDE.md session scope).

## Problem

Cropper has one look today: the B/W "HP5" filter (`src/hp5_emulate.py`). The user built and tuned a colour portrait
look, "MoodPortrait" (built under the name "Rembrandt"), in their other project FujiVibe and wants it in Cropper.
The look is a warm, low-key, earth-tone grade, a pool of light on the face with everything else sinking into dark
umber, and a coarse canvas-tooth grain. The pool of light and the grain are the parts the user liked most.

## Reference (read-only, do not copy personal photos into this repo)

Source of truth is FujiVibe at `C:\Users\vibha\Documents\Projects\FujiVibe`:

| What | Where |
|---|---|
| Design, shipped values, rejected options | `.scratch/rembrandt/spec.md`, `docs/adr/0015-rembrandt-portrait-look.md` |
| Colour grade (maths) | `render/.../tools/RembrandtCorrection.kt` |
| Baked LUT (32-point `.cube`, sRGB in/out) | `derived-luts/Rembrandt sRGB.cube` |
| Pool of light + no-face oval | `render/.../FalloffRenderPipeline.kt` |
| Canvas grain (reference only, NOT ported) | `render/.../GrainRenderPipeline.kt` (profile `REMBRANDT_PROFILE`), `NoiseGrid.kt` |
| Face file format | `.scratch/rembrandt/tools/make_faces.py`: `centerX centerY width height rollRadians` |
| Renders the user liked | `.scratch/rembrandt/rendered/face-pool/` (on disk, not in git) |

Pipeline per photo, in this order: **LUT -> face pool of light -> grain** (in Cropper the grain step is Cropper's own existing grain, see below). Face detection runs on the *source*; the
pool's brightness cap reads the face's brightness from the *graded* image. Each stage rounds to 8-bit, as the
reference does.

## Approach: reproduce in numpy, no JVM

Port the three stages to numpy in a new `src/moodportrait.py`, with the maths and constants taken from the Kotlin.
No JVM dependency, no MediaPipe. Reasons: Cropper is a PySide6 app frozen with PyInstaller (a JVM sidecar would
break that); the stages are plain per-pixel maths; the existing HP5 code is already numpy.

1. **Grade**: use `Rembrandt sRGB.cube` directly (vendored into `src/luts/`, bundled via `cropper.spec` `datas`),
   trilinear interpolation, red-fastest data order, 8-bit round on output. Do **not** re-derive the curve in Python;
   the `.cube` is the artefact the user approved. (A Python copy of `RembrandtCorrection` is only worth having as a
   test oracle for the LUT, see ticket 01.)
2. **Pool of light**: a direct port of `applyFaceLight` / `applyOval` with the shipped `REMBRANDT_PROFILE` values
   (below), vectorised.
3. **Grain: not ported.** Decision 2026-11-11: Cropper already has user-controllable grain (the "Apply grain" checkbox and
   "Grain size"), so MoodPortrait does not carry its own canvas-tooth grain (FujiVibe: 320 cells, opacity 0.10, seed 42).
   The grain is applied by Cropper's existing code after the grade and pool of light. Difference to report: Cropper's
   grain is the HP5-style two-layer grain (`hp5_emulate.make_grain`), not FujiVibe's coarse canvas texture, so output
   will not match FujiVibe's grain. The prototype samples were made without grain for this reason.

### Shipped values (must be preserved exactly)

`FalloffProfile` (face light): `poolInner` 0.9, `poolSigma` 1.1, `poolMinHalfSize` 0.20 (of image width),
`faceStrength` 0.94, `ceilingRatio` 1.5, `ceilingMin` 0.45, `ceilingMax` 0.70, `ceilingFrom` 0.8, `ceilingOver` 0.5,
`shadowWarmth` 0.16, `ground` (0.06, 0.035, 0.02) = `#0F0905`.
Ceiling curve `x / sqrt(1 + (x/c)^2)` (strictly increasing). Pool: oval in the face's own tilted axes, fully lit to
`poolInner`, then `exp(-0.5*((d-poolInner)/poolSigma)^2)` tail. Luma weights 0.2126 / 0.7152 / 0.0722.

No-face fallback (frame-centred oval): `centerX` 0.5, `centerY` 0.42, `radiusX`=`radiusY` 0.58, `innerRadius` 0.35,
`outerRadius` 1.0, `strength` 0.92, smoothstep edge.

Grade (for the LUT test oracle): WB red x1.04 / blue x0.93; `x^1.45` then S-curve p=1.35; hue-family saturation
(warm 0.92, magenta 0.55, cool 0.30; boundaries 65/95/255/295/345 deg); umber `(0.26,0.15,0.07)` shadow tint 0.30,
cream `(1.00,0.975,0.89)` highlight multiply.

### Tried but switched off: keep as parameters, default off

Preserved in the profile as named parameters, default **off**, with a test that off == the shipped output:
`foreheadStretch` (1.35 tried, shipped 1.0), `shadowLift` (0.08 tried, shipped 0.0), and the cap moved out
(`ceilingFrom` 1.1 with `ceilingRatio` 1.0, `ceilingMin` 0.30; shipped 0.8 / 1.5 / 0.45). The ADR is explicit that
the user preferred the look without them; do not enable them, and do not "fix" the known flaws (halo, grey forehead
patch, dark eyes, dulled bright clothes, only the largest face used). No strength slider (out of scope in FujiVibe).

## Where it fits in Cropper

`render_photo()` in `src/pipeline.py` is: crop -> LANCZOS resize to inner size -> `H.emulate` -> paste on white
canvas (border). MoodPortrait slots in where `H.emulate` is, as a third look next to HP5 (B/W) and HP5-style
colour-with-grain, and **the border stays clean** (filter before border, as today).

Consequences to get right:

- **The look is applied to the crop, not the original frame.** The pool of light, the 20%-of-width minimum pool and
  the grain cell count are all relative to the image the filter sees. This is correct for Cropper (it renders what is
  inside the frame) but means a Cropper output only matches a FujiVibe render when the crop is the full frame.
- **Face detection runs once on the EXIF-corrected original**, producing fractions of the *original*. For the filter
  those are remapped into crop coordinates (`(c - x0) / (x1 - x0)`, same for size). The filter
  needs one `Face` (largest) with a roll, from the BlazeFace finder (ticket 04), not from the YuNet triage pass.
- `apply_escalation`, `apply_manual_crop` and `load_preview` all call `render_photo`/re-render, so they must carry the
  look and a face. Store the face on `PhotoJob` rather than re-detecting on each re-render (this mirrors FujiVibe's
  `CachingFaceProvider`).
- Settings (`AppSettings`), `ProcessFolderWorker`, `InputPanel.process_requested` (a 7-arg signal) and
  `main_window._start_processing` all thread `apply_bw`/`apply_grain`/`grain_size`; a "look" choice needs adding there
  with a backward-compatible default.

## Face detector: BlazeFace for the filter, YuNet unchanged elsewhere

FujiVibe tuned against MediaPipe BlazeFace (short range) boxes (eyebrows to chin) with roll from the eye keypoints.
Cropper's YuNet (`src/detection.py`) is kept for triage and cropping; the filter gets its own BlazeFace face finder.

**Decision (2026-11-11, from a scratchpad prototype, not committed):** four FujiVibe photos rendered through a numpy
prototype. With BlazeFace faces the output matched the FujiVibe renders to about 1.8/255 mean absolute difference
(grain excluded). With YuNet faces: 3.6 to 8.7 on three photos and 28.3 on the hat portrait, where YuNet missed the
real face at 2000x3000 (found a shirt crest instead) and found nothing at 24 MP. YuNet is scale-sensitive, and its
boxes also run smaller than BlazeFace's. The user judged the BlazeFace render good, so the filter uses BlazeFace.

Implementation (ticket 04): measure `mediapipe`'s size and Python 3.14 behaviour first; use it if acceptable, else load
the same `.tflite` through OpenCV and port the anchor/decoding/NMS. Detect on a copy of about 1600 px on the long edge.
Cost to watch: the PyInstaller build is 360 MB already.

## Performance

Reference is CPU on the JVM, a few seconds for 24 MP. A first numpy trilinear LUT, unoptimised, measured here:
**3.5 s for 2300x1840 (about the default 2400 canvas) and 16 s for 24 MP**, for the LUT alone; the pool and grain
add a pass each (estimate 1-3 s more at 24 MP, not measured). So fixed-canvas mode (the default) is a few seconds a
photo, and the planned "original size" mode (`.scratch/original-size-output`) at 24 MP would be tens of seconds.
Ticket 01 includes row-chunking, with a thread pool if needed, to cut that; target: under 3 s at the default canvas.
No new GUI machinery is needed: `ProcessFolderWorker` is already a `QThread` that processes one photo at a time, emits
each result as it is ready and supports Stop. A per-photo progress indication already exists as cards appearing; a
within-photo progress bar is only worth adding if original-size mode lands and a photo takes more than about 10 s.

## Out of scope

Strength slider; skin-tone retuning (only medium-brown skin was tested); multiple faces (largest only); a directional
key light; the X-T5 recipe; HEIC/RAW/PNG (D3: JPEG only); any FujiVibe test photo in this repo.

## Decisions to settle with the user (open)

- **D1 Batch or single photo? (DECIDED 2026-11-11: folder-only, like every other look)** Cropper already works on folders. Recommendation: keep folder-only behaviour, same as
  every other look.
- **D2 Scope of the look (DECIDED 2026-11-11: full look; grain via Cropper's own controls)**: full look (LUT + pool of light + grain) or LUT only? A LUT alone cannot do the pool or the
  grain. Recommendation: full look; offer "LUT only" as a later option only if wanted.
- **D3 Input formats (DECIDED 2026-11-11: JPEG only)**: Cropper accepts only `.jpg`/`.jpeg` today and applies EXIF rotation already. Is that enough
  or are HEIC/RAW needed? HEIC would add `pillow-heif`; RAW would add `rawpy` and a demosaic/colour decision.
- **D4 (new, deferred: detailed discussion later)** How does the look appear in the UI: replacing the "Apply B/W filter" checkbox with a Look selector
  (None / B&W HP5 / MoodPortrait), or a separate checkbox? Affects grain controls (HP5 grain size does not apply).
- **D5 (new, effectively settled: RGB output with the existing white border)** Output colour: the look is colour; confirm the existing `mode "L"` canvas path is only for B/W.

## UI discussion so far (2026-11-11)

- The look is for portraits. Two ways of using it, same pipeline: a folder of portraits, or a mixed set of photos that
  Cropper crops into portraits; MoodPortrait is applied after the crop if selected. No separate UI modes needed.
- One Look choice (None / B&W HP5 / MoodPortrait) is the working assumption; Cropper's grain controls stay.
- No face: the user chooses whether to apply the look to a run; no skip logic. The frame-centred oval is used and the
  card should say no face was found. Same for group photos: the user decides.
- Group photos means up to two large faces. DECIDED: light both. Each large face (area at least about half the
  largest) gets its own pool; darkening applies only away from all of them. With one qualifying face the output must stay
  identical to today's. Not tuned by FujiVibe: the user reviews it on two-person photos they supply (none available yet).
- The look applies to every photo in a run (settings are per run, not per photo); the user unticks Keep on unwanted ones.
- Separate ticket candidate: YuNet (which positions crops) can miss faces on large photos; run it on a downscaled copy.

## Tickets

`issues/01` LUT grade and fast apply; `02` face pool of light and no-face oval; `03` canvas grain (dropped, use Cropper's grain);
`04` face source (YuNet to `Face`, calibration check); `05` pipeline + settings + GUI integration; `06` parity check
against FujiVibe renders; `07` extra input formats (dropped, JPEG only).
