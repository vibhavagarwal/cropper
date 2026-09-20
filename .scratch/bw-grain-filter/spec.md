# Split "Apply HP5 filter" into independent B/W and grain controls

Status: designed 2026-09-20, approved by user, **implementation deliberately not started**
(user asked to write up the design only, no development yet).

## Context

Grew out of a UI observation during manual testing of the post-v1 cleanup work: unchecking
"Apply HP5 filter" still produced a black-and-white photo. Root cause: the entire pipeline is
built around the Ilford HP5 recipe (see `docs/filter_hp5_notes.md`), and `render_photo`
(`src/pipeline.py`) always renders onto a grayscale (`"L"` mode) canvas — the checkbox only ever
controlled whether the tone-curve/grain emulation ran, never whether the output was color or
black & white. This was flagged as "by design, not a bug" but the user asked for the feature to
actually support color output, decomposed into two independent controls plus a grain-size
option.

## Decisions (resolved during brainstorming, 2026-09-20)

1. **Unchecking "Apply B/W filter" means full original color** — no desaturation, no HP5 tone
   curve at all. Not "color with the tone curve applied."
2. **Grain size is a Small / Medium / Large preset dropdown**, not a raw numeric multiplier or
   slider. Medium reproduces today's tuned constants exactly (backward-compatible default look).
3. **"Apply grain" is fully independent of "Apply B/W filter"** — all 4 combinations are valid
   and selectable:
   - B/W + grain → today's existing HP5 look (default, unchanged)
   - B/W only → flat monochrome, no grain (today's "unchecked" behavior, now reachable
     explicitly rather than being the accidental result of "off")
   - Color + grain → grainy color photo (new capability)
   - Neither → original color, untouched apart from crop/resize/border (new capability)
4. Grain on a color image is **not** independent per-channel noise (that would look like color
   speckling/chromatic noise) — the same grain field is added identically to all three RGB
   channels, so it still reads as film grain regardless of whether B/W is on.

## Design

### 1. Core pipeline (`src/hp5_emulate.py`)

- Factor the existing WB-gain + gray-mix + tone-curve + soften logic out of `emulate()` into a
  `to_bw(img, p)` step. Unchanged math, just extracted so it can be skipped.
- `make_grain()` gains a `size` multiplier: `small=0.5x`, `medium=1.0x` (today's `grain_cell`,
  `grain_amp`, `grain_fine_amp` values, unchanged), `large=2.0x`, scaling all three constants
  together.
- Grain application generalizes from "add to the single luma channel" to "add the same noise
  field to every channel present" (1 channel for grayscale, 3 for color).
- `emulate(img, seed, p=PARAMS, apply_bw=True, apply_grain=True, grain_size="medium")` becomes
  the single entry point covering all 4 combinations. Defaults preserve today's behavior, so the
  standalone CLI (`process_file`/`main`, which always wants the full HP5 look) needs no changes.

### 2. Settings & data flow

- `AppSettings` (`src/settings.py`): replace `apply_filter: bool` with `apply_bw: bool = True`,
  `apply_grain: bool = True`, `grain_size: str = "medium"`. The loader already ignores unknown
  fields (see `test_load_ignores_unknown_fields_gracefully`), so old settings.json files with a
  stale `apply_filter` key degrade gracefully to the new defaults rather than erroring.
- `PhotoJob` (`src/pipeline.py`): same three fields replace `apply_filter`, threaded through
  `process_photo`, `process_folder`, `apply_escalation`, `apply_manual_crop`, and `render_photo`
  (mechanical signature changes, no new logic beyond what's in section 1).
- `render_photo` picks the canvas mode from `apply_bw` (`"L"` when checked, `"RGB"` otherwise)
  and calls the new `emulate(...)` with all three flags/values.

### 3. GUI

- `InputPanel` (`gui/input_panel.py`): replace the single "Apply HP5 filter" checkbox with two
  checkboxes — "Apply B/W filter" and "Apply grain" — plus a "Grain size" `QComboBox`
  (Small/Medium/Large), all inside the existing "Run settings" group box from the post-v1
  cleanup pass.
- `process_requested` signal grows from `(folder, shape, canvas_long, apply_filter)` to
  `(folder, shape, canvas_long, apply_bw, apply_grain, grain_size)`.
- `MainWindow._start_processing` picks up the expanded signature the same way it does today.

### 4. Testing

- New unit tests in `tests/test_layout_and_filter.py` covering the 4 B/W×grain combinations
  (canvas mode, that "color" combinations actually retain color, that grain differs
  detectably between size presets) using TDD as established for this repo.
- Existing tests referencing `apply_filter` in `tests/test_pipeline.py`, `tests/test_settings.py`,
  and `tests/test_gui_smoke.py` get updated to the new three-field shape (not left broken/skipped).

## Out of scope

- No numeric/slider grain control — presets only (per decision 2).
- No change to the border step, crop logic, escalation, or any other pipeline stage.
- No retroactive migration of old `apply_filter` settings values onto the new fields beyond the
  loader's existing graceful-default behavior.

## Next step

Broken into three implementation-ready tickets under `.scratch/bw-grain-filter/issues/`:
`01-pipeline-split.md`, `02-settings-and-pipeline-threading.md`, `03-gui-wiring.md`, in that
dependency order. Implementation itself has not started — handed off to a separate session.
