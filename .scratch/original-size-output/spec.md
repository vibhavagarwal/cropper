# Original-size output

## Problem

Output size is set by a fixed "Canvas long edge" (default 2400, range 200-10000). Every photo is
resized to that canvas, so large sources lose detail and small ones are upscaled. A user who wants
the best resolution each photo can give has no way to ask for it (a 600 px canvas yields 600x480).

## Goal

An "Original size" option that sizes each output from its own source, never upscaling.

## Behaviour

- New canvas mode alongside the existing fixed long edge: "Original size".
- The photo is cropped to the usual inner ratio (composition logic unchanged), and the crop is
  rendered at its native pixel size, with no resample.
- Canvas = crop size + border on each side. Border stays a fraction of the canvas long edge
  (existing `border_size` presets), rounded to whole pixels.
- Output dimensions therefore vary per photo. Aspect ratio of the canvas still follows the chosen
  shape.
- Grain and the other long-edge-relative filter sizes already scale with resolution
  (`docs/filter_hp5_notes.md`), so they need no change.
- Fixed-canvas mode stays the default and behaves exactly as today.

## Design wrinkle

`layout()` derives the inner ratio from the canvas size, and the crop needs the inner ratio, while
original-size mode wants the canvas to come from the crop. The two depend on each other. Break the
loop by cropping to the ideal ratio first, then solving for the canvas, or by iterating once.
Whichever is chosen, the final canvas must be exactly the shape's ratio within rounding and the
border exactly uniform.

## Locked decisions this touches

The README says border and layout math stay locked. This changes how the canvas is derived, not
the border fraction or the inner-ratio crop target. Confirm that reading before starting.

## Out of scope

Upscaling, a max-edge cap, per-photo overrides, changes to detection/triage/crop logic.
