# Change default grain_size and border_size to "medium"

Status: requested 2026-09-21, not scoped

## User's request

Both `grain_size` and `border_size` should default to `"medium"`.

## Current state (checked, not changed)

- `grain_size` (`src/settings.py:14`, `AppSettings.grain_size: str = "medium"`) - **already
  `"medium"`, no change needed there.** Set when `.scratch/bw-grain-filter/` shipped, with
  `medium` explicitly defined as "today's tuned constants, unchanged" - i.e. it was already
  chosen as the no-visual-change-on-upgrade default.
- `border_size` (`src/settings.py:15`, `AppSettings.border_size: str = "small"`) - currently
  `"small"`, would need to change to `"medium"`.

## Tension with a prior explicit decision

This directly reverses a decision made when border-size presets were scoped and implemented
(`.scratch/triage-and-border-tuning/issues/02-configurable-border-size-presets.md`, decision 2):
*"Default stays 'small' (2%, unchanged) — matches today's output exactly on upgrade... This does
not by itself fix the 'border looks too small' complaint — the user will need to manually select
medium/large. That tradeoff (explicit, unchanged default vs. an immediately-different look on
upgrade) was confirmed deliberately, not overlooked."* This request supersedes that tradeoff -
worth flagging explicitly as a deliberate reversal when this gets implemented, not a quiet
change, same as the gallery-grid ticket's handling of its own prior-decision reversal
(`.scratch/post-qss-visual-feedback/issues/02-...md`).

## Likely fix shape (not scoped/decided, just the obvious touch point)

`src/settings.py`: `AppSettings.border_size` default `"small"` → `"medium"`. Everywhere else
already reads the default *from* `AppSettings` (`gui/input_panel.py`'s
`border_size_combo.setCurrentText(initial_settings.border_size)`, `layout()`'s own
`border_size="small"` parameter default in `src/hp5_emulate.py` is a separate, lower-level
default used only when `AppSettings` isn't in the call path - e.g. direct `layout()` calls in
tests/CLI - worth deciding whether that should also move to `"medium"` for consistency, or stay
`"small"` as the library-level "untouched" default with `AppSettings` being the only thing that
actually changes for the GUI path).

Existing tests that assert the `"small"`/unchanged default (e.g. `tests/test_settings.py`'s
`test_load_missing_file_returns_defaults`, `tests/test_layout_and_filter.py`'s
`test_border_size_small_matches_todays_default`-style regression pin) will need review once this
is scoped - some assert the *default* (would need updating), others assert `border_size="small"`
explicitly as one of three presets (should stay as-is, since `"small"` still needs to exist and
work correctly as a preset, just not be the default anymore).

## Comments
