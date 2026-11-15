# Add an "Original size" canvas mode

Status: needs-triage
Spec: ../spec.md

## What to build

Let the user choose "Original size" instead of a fixed canvas long edge, so each photo is saved at
its native crop resolution, never upscaled.

## Steps

1. Layout: add a layout path in `src/hp5_emulate.py` that takes the source crop size and returns
   canvas, border and inner, with border from the existing `border_size` preset. Resolve the
   inner-ratio / canvas circularity described in the spec.
2. Pipeline: in `src/pipeline.py`, `process_photo` and `render_photo` skip the LANCZOS resize to
   the inner size in this mode (crop pixels are used as-is). Re-render paths (`load_preview`, the
   escalation and crop-editor re-renders) and `PhotoJob.canvas_long` must handle the mode.
3. Settings: add the mode to `src/settings.py` with a backward-compatible default (fixed canvas).
4. GUI: in `gui/input_panel.py`, add an "Original size" checkbox (or equivalent) that disables
   `canvas_spin`, and thread it through `process_requested`. Check the settings row still wraps
   at narrow widths (see the existing regression test).
5. Check `gui/detail_view_dialog.py` and `gui/crop_editor_dialog.py`, which call `H.layout`
   directly, for the new mode.

## Acceptance

- Original size on: output pixel dimensions equal crop size plus 2x border, with no resample, and
  a large source is not downscaled.
- Output canvas matches the chosen shape's ratio within rounding; border is uniform.
- Original size off: output is byte-for-byte unchanged from today for the same inputs.
- Setting persists across launches and old settings files still load.
- Tests: layout math for all three shapes and border sizes, a pipeline test for native-size output,
  a GUI smoke test for the control, and a settings round-trip.

## Comments
