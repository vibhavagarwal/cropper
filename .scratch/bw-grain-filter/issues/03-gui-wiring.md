# Replace the single filter checkbox with B/W + grain + grain-size controls

Status: ready

## Context

Depends on tickets 01 and 02. See `.scratch/bw-grain-filter/spec.md` section 3 for the full
design.

## Design

- `gui/input_panel.py`: replace the single "Apply HP5 filter" `QCheckBox` with two checkboxes —
  "Apply B/W filter" and "Apply grain" — plus a "Grain size" `QComboBox` with items
  `["small", "medium", "large"]` (default `"medium"`), all inside the existing "Run settings"
  `QGroupBox` added during the post-v1 UI cleanup pass (`gui/input_panel.py:settings_group`).
- `InputPanel.process_requested` signal grows from
  `Signal(str, str, int, bool)` (folder, shape, canvas_long, apply_filter) to
  `Signal(str, str, int, bool, bool, str)` (folder, shape, canvas_long, apply_bw, apply_grain,
  grain_size).
- `gui/main_window.py`: `MainWindow._start_processing` picks up the expanded signature the same
  way it does today (persists to `self.settings`, passes through to `ProcessFolderWorker`).
- `gui/workers.py`: `ProcessFolderWorker.__init__` and `.run()` take `apply_bw`/`apply_grain`/
  `grain_size` instead of `apply_filter`, passing through to `pipeline.process_folder`.

## Testing

TDD, updating rather than leaving behind:
- `tests/test_gui_smoke.py` `InputPanelTests`: defaults-from-settings and
  process_requested-emits-current-values tests need the new checkboxes/dropdown instead of the
  old single checkbox.
- `MainWindowWiringTests`/`ProcessFolderWorkerTests` call sites that currently pass a single
  `apply_filter` bool to `_start_processing`/`ProcessFolderWorker(...)` need updating to the
  three-value shape.
- Add a smoke test that toggling "Apply B/W filter" off and processing a color synthetic photo
  produces a gallery card whose rendered thumbnail is NOT grayscale (real per-channel variance).

## Manual smoke check

Since this is UI-facing: run the app, process a folder with both checkboxes toggled through all
4 combinations, and manually verify the review gallery thumbnails match the design's 4 outcomes
(HP5 look / flat B&W / grainy color / plain color). Try all 3 grain-size presets with grain on
and visually confirm the size difference.

## Out of scope

- No menu bar or other structural addition (same constraint as the earlier UI cleanup ticket).
- No numeric/slider grain control — presets only.
