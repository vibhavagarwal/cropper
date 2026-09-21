# Border size: small / medium / large presets (currently fixed, and reads as too small)

Status: ready — scoped 2026-09-21

## Context

The white border added around the final photo is currently a fixed, hardcoded 2% of the canvas
long edge — `PARAMS["border"] = 0.02` in `src/hp5_emulate.py`, explicitly commented as
`# Border (LOCKED): white, 2% of long edge, added after the filter`. `layout()`
(`src/hp5_emulate.py:160-170`) uses this fixed value as the default `border_frac` for every
shape/canvas-size combination, and the GUI pipeline path (`src/pipeline.py:render_photo`) always
calls `H.layout(shape, canvas_long)` with no override — there is currently no way to change the
border size from the GUI at all. (The standalone CLI does have a `--border` float override, but
that path isn't used by the GUI/pipeline.)

## User's request

The border currently looks too small in practice. Wants it configurable as presets — small /
medium / large — the same UX pattern as the grain-size dropdown just added
(`.scratch/bw-grain-filter/`), not a raw numeric field.

## Decisions (resolved during scoping, 2026-09-21)

1. **Presets: small = 2%, medium = 4%, large = 6%** of the canvas long edge.
2. **Default stays "small" (2%, unchanged)** — matches today's output exactly on upgrade, same
   convention as grain-size's `medium="today's tuned constants, unchanged"`. This does **not**
   by itself fix the "border looks too small" complaint — the user will need to manually select
   medium/large. That tradeoff (explicit, unchanged default vs. an immediately-different look on
   upgrade) was confirmed deliberately, not overlooked.
3. On the "LOCKED" comment in `PARAMS`: not investigated further (no ADR/spec history check
   done) — the user's explicit request to make this configurable stands regardless of why it was
   originally locked.

## Design

Mirrors the grain-size feature's shape almost exactly — same three-ticket breakdown is a
reasonable template (`.scratch/bw-grain-filter/issues/01-03`):

1. **`src/hp5_emulate.py`**: `layout(shape, canvas_long, border_frac=None)` already accepts an
   override — add a `border_size: str = "medium"` parameter (or reuse a `BORDER_SIZE_MULT`-style
   dict like `GRAIN_SIZE_MULT`, e.g. `{"small": 0.02, "medium": 0.04, "large": 0.06}`) that
   `layout()` uses to pick `border_frac` when no explicit override is given, defaulting through
   to today's constant. Decide whether `PARAMS["border"]` stays as the "small"/default constant
   or becomes redundant with the new mapping — avoid having two sources of truth for the same
   value.
2. **`src/settings.py`**: `AppSettings` gets a new `border_size: str = "small"` field (default
   per decision 2 above).
3. **`src/pipeline.py`**: `PhotoJob` gets `border_size: str`, threaded through
   `process_photo`/`process_folder`/`apply_escalation`/`apply_manual_crop`/`render_photo` the
   same way `grain_size` was — `render_photo` already calls `H.layout(shape, canvas_long)`;
   thread `border_size` into that call.
4. **`gui/input_panel.py`**: new `QComboBox` ("Border size:", items `["small", "medium",
   "large"]`, default from `initial_settings.border_size`), added to the `settings_group` row
   alongside the grain-size dropdown. `process_requested` signal grows by one more `str`
   argument.
5. **`gui/workers.py` / `gui/main_window.py`**: thread `border_size` through
   `ProcessFolderWorker` and `_start_processing`, same pattern as `grain_size`.

## Testing

Same shape as the grain-size regression pin and combination tests in
`.scratch/bw-grain-filter/issues/01-pipeline-split.md`'s testing section:

- `layout(shape, canvas_long, border_size="small")` reproduces today's exact output (regression
  pin — same canvas/border/inner dimensions as calling `layout()` without the new parameter).
- `layout(..., border_size="medium")` and `"large"` produce measurably different (larger)
  border thickness than `"small"`, proportional to the 2%/4%/6% mapping.
- `AppSettings` round-trip/default tests for the new `border_size` field (default `"small"`).
- `PhotoJob`/`process_photo`/`render_photo` threading tests, mirroring
  `tests/test_pipeline.py`'s existing `apply_bw`/`apply_grain`/`grain_size` coverage.
- `InputPanel` tests for the new combo box (defaults from settings, appears in
  `process_requested`'s emitted values, grouped in `settings_group`).

## Comments
