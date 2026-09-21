# First-load window layout: oversized middle section, spacing looks off

Status: reported — no fix requested yet, note only

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

## User's suggested fix for the output-folder-label placement

Move `output_folder_label`'s text to sit next to the "Choose output folder..." button (in the
bottom button row) instead of floating alone between the Run settings box and the gallery. This
would also address part of the "large empty gap" complaint above by removing that label from
the middle section entirely, not just tightening the Run settings box's own spacing.

## Notes for whoever picks this up

- User said explicitly: no change needed right now, just capture for later.
- More items from the same live-testing session may follow — check this file's parent
  `spec.md` for an updated issue list before starting.

## Comments
