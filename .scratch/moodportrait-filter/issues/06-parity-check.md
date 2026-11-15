# Compare Cropper's render with FujiVibe's and report differences

Status: resolved
Spec: ../spec.md
Blocked by: 01, 02

## What to build

A local-only script (not run in CI, not committed with any photos) that renders a FujiVibe test photo through the
Cropper MoodPortrait stages using the FujiVibe `.face.txt` (so the face is identical) and diffs it against
`.scratch/rembrandt/rendered/face-pool/<name>-rembrandt.jpg`.

## Steps

1. Input must be the **full frame, upright, with no Cropper crop/resize**, since FujiVibe rendered the whole image
   (HEIC ones were converted to JPEG first; the converted copies are not in the repo, use the four JPEG originals or
   convert with ffmpeg into the scratchpad).
2. Compare stage by stage if a render differs: LUT only, then + pool. Grain is excluded: Cropper's grain differs from FujiVibe's, so compare with grain off
   and expect the reference's grain to show as a small residual difference. Report mean/max abs difference and
   the share of differing pixels. The reference output is a **JPEG**, so compare against a decode of it and expect
   compression noise; allow a small tolerance and say what it was.
3. With the same face file expect near-identical (rounding only). Then repeat with Cropper's own BlazeFace finder
   (ticket 04) to confirm it reproduces the same faces.
4. Write the differences found into this ticket's Comments and `docs/filter_moodportrait_notes.md`.

## Acceptance

- [ ] Same-face comparison within rounding on every available photo, or the cause of each difference explained
- [ ] Cropper's own BlazeFace face compared with the `.face.txt` files and the renders (visual side-by-side, not only numbers)
- [ ] No personal photo or render committed

## Comments

`tools/moodportrait_parity.py <fujivibe .scratch/rembrandt> <out dir>`. Results (grain excluded in ours): same face file 1.66-1.88 mean abs diff, p99 7-10; Cropper BlazeFace 1.76-2.40 (puppets worst: roll 3 degrees off, 4.2% of pixels >8). Differences summarised in `docs/filter_moodportrait_notes.md`. Only 4 of 7 photos available as JPEG; the three HEIC ones were not tested.
