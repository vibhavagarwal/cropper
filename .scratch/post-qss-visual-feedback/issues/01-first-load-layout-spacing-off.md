# First-load window layout: oversized middle section, spacing looks off

Status: ready

## Observed

Screenshot from the user's first run of the app after the QSS pass. On first load (empty
gallery, no folder processed yet):

- The "Run settings" group box is much taller than its contents need — Shape/Canvas/checkboxes/
  grain-size dropdown sit roughly vertically centered inside a large mostly-empty box, with
  significant blank space above and below the actual row of controls.
- The `output_folder_label` ("Output folder: C:/Users/vibha/Pictures/CropTest/Outputs") sits
  alone, floating in a large empty gap between the Run settings box and the "Running cost" /
  gallery area below — visually disconnected from both.
- Overall the "middle section" of the window (between the folder picker at top and the gallery
  grid at bottom) is taking up far more vertical space than its content needs, while the
  gallery/photo-review area — arguably the most important part of the window — is
  comparatively small and pushed to the bottom.

## Likely area (not investigated, just a starting guess for later)

Probably a layout stretch-factor issue in `gui/main_window.py`'s central `QVBoxLayout`
(`input_panel` / `output_folder_label` / `busy_indicator` / `gallery` / `bottom_row`) — nothing
currently gives the gallery an explicit stretch priority over the settings/label area above it,
so on a tall window with an empty gallery, the extra space is likely being distributed to the
wrong widgets by default Qt sizing behavior, rather than being given to the gallery (which is
the one thing that should grow) or trimmed from the mostly-empty group box (which should stay
compact). Not investigated further — no code read yet, this is a guess for whoever picks it up.

## Decisions (resolved during scoping, 2026-09-21)

1. **Move `output_folder_label` into the bottom button row**, next to "Choose output folder..."
   (confirmed by the user), instead of its own standalone widget between the Run settings box
   and the gallery. Removes it from the middle section entirely.
2. **Give the gallery explicit stretch priority** in `MainWindow`'s central `QVBoxLayout` so it
   grows to fill available vertical space, while the Run settings group box and folder-picker
   row stay their natural compact size instead of being stretched by default Qt sizing
   behavior. Concretely: add a stretch factor favoring `self.gallery` when adding widgets to the
   central layout (e.g. `layout.addWidget(self.gallery, stretch=1)`, with `input_panel`/
   `busy_indicator` left at their default stretch of 0), and verify the "Run settings" group box
   itself isn't independently expanding (check its size policy if the stretch factor alone
   doesn't fix it).

## Design

- `gui/main_window.py`: remove `self.output_folder_label` from the central layout; instead add
  it (or its text) into `bottom_row`, positioned next to `choose_output_button`. Keep
  `_update_output_folder_label()`'s existing "Output folder (default): ..." / "Output folder:
  ..." text logic — this is a placement change, not a text/behavior change.
- `gui/main_window.py`: central layout stretch fix as described above.

## Testing

- Existing tests referencing `output_folder_label` (`test_output_folder_label_shows_default_before_save`,
  `test_output_folder_label_reflects_chosen_override` in `tests/test_gui_smoke.py`) should still
  pass with the label just relocated — update only if they assert on layout position, not just
  text content.
- No new behavior to test for the stretch-factor fix beyond a visual check (Qt layout stretch
  isn't meaningfully unit-testable) — manual verification in the running app is expected here.

## Comments
