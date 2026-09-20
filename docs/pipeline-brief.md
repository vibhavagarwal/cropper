> Note: this was the project brief from the original `photo-pipeline-starter.zip` (that
> package's own `CLAUDE.md`). It lives here, not at the repo root, because this repo's
> `CLAUDE.md` is a different document (agent-skills config). See `.scratch/desktop-tool/spec.md`
> for the desktop tool requirements that supersede this brief's "Suggested first steps" section.

# Travel photo batch pipeline: crop, filter, border

Read this first. It is the project brief and the record of decisions so far.
Status date: 2026-09-20.

## Purpose

Batch process a folder of travel photos with real composition judgment (not just a fixed
aspect ratio cut) while keeping cost and human effort as low as possible. The design
principle is to run cheap deterministic code on everything and spend paid AI judgment only on
the photos where the cheap checks cannot give a clear answer.

## What exists and what does not

Built and tested (see `src/hp5_emulate.py`, `tests/`):
- Landscape-theme filter: black and white emulation of the Ilford HP5 Plus 400 Fujifilm recipe
- Fixed-size canvas layout for three shapes, white border, exact output dimensions

Not built yet:
- EXIF correction step as its own module (the script only calls `ImageOps.exif_transpose`)
- Detection pass (faces, saliency, symmetry)
- Triage gate and its numeric thresholds
- Crop stage (formula crop and the escalated AI crop decision)
- Theme routing (landscape vs portrait theme)
- Filter for the portrait theme
- Tool integration, where the shape and canvas size get selected

Earlier exploratory scripts from a manual proof of concept (face and saliency detection,
cropping) live in an older chat and are not included in this package.

## Pipeline, in locked order

1. EXIF orientation correction. Coded, free, always runs. The source camera stores rotation as
   a flag instead of rotating pixels (6 of 9 test files carry orientation 8), so analysis on raw
   pixels sees the photo sideways. This is a data correctness fix, not a composition judgment.
2. Detection pass. Coded and free: face detection (Haar cascade), saliency mapping (OpenCV
   spectral residual), and a symmetry test (mirror flip pixel comparison). No tilt or line angle
   detection and no perspective or keystone correction of any kind. The workflow assumes photos
   are shot at the orientation the user intends and only crops.
3. Triage gate. Coded and free. Decides per photo whether to escalate to paid reasoning or to
   handle it with a formula. Escalate when any of these hold:
   - saliency spans nearly the whole frame (a null signal)
   - multiple faces with no clear primary subject
   - a saliency blob touches an edge or corner (proxy for a stray object)
   - the symmetry score is ambiguous (not decisive either way)
4. Non-escalated photos. Coded crop using rule of thirds and symmetry math: subject center at
   1/3 or 2/3, symmetric subjects centered. Subject position and headroom are computed as exact
   fractions of the crop and checked against the 1/3 and 2/3 targets, not eyeballed. Symmetry is
   confirmed by the mirror flip comparison instead of assumed.
5. Escalated photos. One combined API call per photo, not several. Image plus detection
   metadata in, crop decision out (with a confidence field). Cheaper model tier first, escalate
   to the stronger tier only if the first reports low confidence. Confirm current model IDs
   and pricing in the Anthropic docs at build time.
6. Rare human review. Only when the stronger tier is also uncertain. This is the "a little
   intervention is fine" allowance, not a routine per-photo or per-escalation step.
7. Crop execution to the INNER ratio of the selected shape (see Output layout).
8. Resize the crop to the inner pixel size. This happens before the filter so grain is sized to
   the final photo and no grain gets resampled.
9. Filter, chosen by photo theme. Landscape theme: HP5 emulation (built). Portrait theme: not
   designed yet.
10. Border, added after the filter so it stays a clean unfiltered frame. Locked decision.
11. Export.

Composition judgment matters in practice. A manual proof of concept on 7 Paris photos found
that both detectors are unreliable often enough that blind trust produces real errors: on one
photo saliency returned almost the whole frame as important. Decisions that needed judgment
were how much surrounding environment to keep versus cropping tight to a subject, recognizing
when a symmetric subject (a cathedral facade) should be centered instead of placed on a thirds
line, and spotting distracting foreground elements (a stray arm or phone) that detection never
flagged.

## Output layout (locked)

The tool lets the user pick the output shape. Canvas size can change and must stay a parameter.

- Shapes: square 1:1, portrait 4:5, landscape 5:4
- Canvas long edge: variable, default 2400 (`--canvas-long`, or `layout(shape, canvas_long)`)
- Border: white, uniform, 2% of the canvas long edge (48px at 2400), applied after the filter
- Inner photo area = canvas minus the border on each side

The crop stage must target the inner ratio, not the canvas ratio, and must ask
`layout(shape, canvas_long)` for it on every run (it drifts slightly with canvas size because
the border rounds to whole pixels). Portrait at 2400: canvas 1920 x 2400, inner 1824 x 2304,
inner ratio 0.7917 (not 0.8). Doing it this way means the output is exactly the canvas size with
no stretching or extra trimming. `render()` rejects a crop more than 0.5% off the inner ratio
and warns if the crop has fewer pixels than the inner size (upscaling).

## Photo themes, not frame orientation

"Portrait" and "landscape" are themes of the photo (people focused vs scenery or place), not
whether the frame is tall or wide. Round 1 covers the landscape theme only. Portrait theme
filtering comes later and the user will define it.

Routing sketch (a suggestion, not a decision): a large face means portrait theme, default is
landscape theme, and ambiguous cases such as small figures in a wide scene escalate. Until the
portrait filter exists, portrait-theme photos should be flagged, not silently given the
landscape filter. The demo runs so far applied the landscape filter to every photo (including
people photos) only to test the code.

## Landscape filter: HP5 recipe emulation

The user's reference look is this recipe (Anders Lindborg, published on Fuji X Weekly):
https://fujixweekly.com/2022/03/23/fujifilm-x-trans-iv-film-simulation-recipe-ilford-hp5-plus-400/
Settings: Monochrome, DR400, Highlight -1, Shadow +1, Noise Reduction -4, Sharpness -2,
Clarity 0, Grain Strong and Large, Daylight white balance with +1 Red and -8 Blue.

The four landscape samples the user supplied were that recipe's own camera-made example photos,
so they are outputs only. No color originals exist for them, which limits how exactly the
filter can be fitted. Source photos in this project are Fujifilm X-T5 JPEGs (7728 x 5152). The
X-T5 supports the recipe in camera, which would be more faithful for future shoots than this
post-hoc emulation.

What the code does: white balance gains, weighted gray mix, a tone curve (slight toe, soft
highlight shoulder, lifted black floor), slight softening, then grain. Every parameter is in
`PARAMS` at the top of `src/hp5_emulate.py`. Details, measurements and tuning history are in
`docs/filter_hp5_notes.md`. Measured targets are in `docs/reference_stats.json`.

Measured versus guessed, kept explicit:
- Measured from the references: black floor near 8 of 255, no clipped highlights, contrast range
- Guessed: white balance gains and channel mix (need a color original paired with its finished
  version to fit), tone curve shape, grain size and amplitude
- Scene dependent, so never fitted as constants: median, white ceiling, tonal spread

## Cost analysis for the AI step

Estimates from an earlier session. Re-verify against current pricing before relying on them.
- Image cost is capped regardless of source resolution (about 1568px long edge, roughly 1600
  tokens per image), so downscale before sending
- One well designed call per photo costs roughly $0.003 to $0.01 depending on model tier
- Replicating the full manual thoroughness with several calls per photo costs 3x to 8x that
- The biggest lever is triage (not calling the model at all when cheap checks are decisive).
  Model choice and prompt trimming matter less
- Batch API (50% discount, asynchronous) and prompt caching for the repeated rubric are
  straightforward extra savings once the triage pipeline exists

## Open items

1. Numeric triage thresholds (how ambiguous a symmetry score must be to escalate, what counts as
   saliency spanning nearly the whole frame, edge touching blob size, the rule for a primary face)
2. Crop stage: formula crop, prompt and JSON schema for the AI crop decision with a confidence
   field, and the fallback when the stronger tier is also unsure
3. Theme classifier and routing
4. Portrait theme filter. Five sample images exist but come from mixed sources and have a
   punchier look (see `docs/filter_hp5_notes.md`)
5. Fit the channel mix and white balance from a color original paired with its finished version
6. Tool integration for shape and canvas size selection
7. Batch runner, config file, and a per-photo decision log (which photos escalated, model used,
   cost) so triage thresholds can be tuned on real batches

## Suggested first steps (suggestions, not decisions)

1. Scaffold a package around `src/hp5_emulate.py` and keep `layout()` and `render()` as the
   only place canvas math lives
2. Build the EXIF and detection modules, then write out the raw metrics per photo to JSON
3. Label a small batch by hand (clear, ambiguous) and pick the triage thresholds from that data
4. Implement the formula crop against `layout()["inner_ratio"]`, then the escalation call

## Conventions

- Accuracy over embellishment. Say what was measured and what was guessed
- Keep date formats and whitespace consistent
- Do not commit personal photos. The test photos include family members. Tests here use
  synthetic images only

## Layout and commands

```
CLAUDE.md                 this file
requirements.txt
src/hp5_emulate.py        filter, layout, border, CLI
docs/filter_hp5_notes.md  recipe, measurements, tuning history, limits
docs/reference_stats.json measured targets from the reference photos
tools/measure_stats.py    luma percentiles for output images
tools/grain_metric.py     rough grain level at 799px
tests/                    unittest suite (synthetic images)
```

```
pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/hp5_emulate.py photos/*.JPG -o out --shape portrait --canvas-long 2400
python src/hp5_emulate.py photos/*.JPG -o out --max-edge 2400      # filter + border, no fixed canvas
python tools/measure_stats.py out/*.jpg
```

In `--shape` mode a plain center crop is used as a placeholder when an image is not already at
the inner ratio. Replace it with the real crop stage.
