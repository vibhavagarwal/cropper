# "Run settings" row labels/controls overlap when the window is narrow

Status: reported 2026-09-21, not scoped, not implemented — note-taking only.

## Context

Live-testing observation, same session as issue 05. Shrinking the main window narrows the "Run
settings" group box (`gui/input_panel.py`'s `settings_group`, a single `QHBoxLayout` row:
Shape / Canvas long edge / Apply B/W / Apply grain / Grain size / Border size). None of these
labels or controls wrap or truncate gracefully - at a narrow-enough window width they visibly
overlap each other instead (e.g. "Canvas long edge:" overlapping its own spinbox, "Apply grain"
overlapping the "Grain size:" label, "Border size:" getting clipped at the window edge). See the
user's screenshot.

## User's request

None yet - explicitly asked to just log this for later rather than fix now.

## Notes for whoever picks this up

- Check `.scratch/post-qss-visual-feedback/spec.md` for the full running list before starting.
- The settings row has grown twice now (grain-size dropdown, then border-size dropdown in
  `.scratch/triage-and-border-tuning/issues/02-configurable-border-size-presets.md`), each time
  adding more fixed-width widgets to the same single `QHBoxLayout` - this is likely the row
  simply running out of horizontal room, not a one-off widget-sizing bug.
- Likely candidates once scoped: wrap the row onto multiple lines at narrow widths (e.g.
  `QFormLayout` or a flow layout instead of a flat `QHBoxLayout`), or give `MainWindow` a
  sensible minimum width that keeps the row from being squeezed below its natural size in the
  first place (there's already a `setMinimumSize` call on `MainWindow` - check whether it
  accounts for this row's actual minimum width).
- Not investigated further - no code changes attempted, this is a live-testing observation only.

## Comments
