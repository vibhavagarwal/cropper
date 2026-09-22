# Show the app logo in the empty gallery state instead of (or alongside) plain text

Status: implemented 2026-09-21, then revised same day. Resolved the "replace vs. both" open
question as **both** - the logo (`gui/assets/branding/logo.png`, `gui/review_gallery.py`'s new
`logo_label`) sits above the existing instructional text, not in place of it, so the "choose a
folder and click Process Folder" instruction is still shown.

Follow-up after the first pass: the user saw a further clipping bug in the dashed `#emptyState`
box (a third recurrence in this same area) and asked to just remove the box and enlarge the
logo instead of chasing more box-sizing bugs. Implemented: `#emptyState`'s QSS background/
dashed-border/padding removed entirely (plain text now), `_LOGO_SIZE` raised from 120 to 200.
The underlying clipping bug was also root-caused and fixed for real, independent of the box's
removal - see `issues/01-...md`.

Window/taskbar icon reuse **was** picked up in the same follow-up (the user asked separately) -
`MainWindow.setWindowIcon()` and `QApplication.setWindowIcon()` (in `gui/main_window.py` and
`gui/main.py` respectively) both now use the same logo file.

## Context

Follow-up to the empty-state work (`.scratch/post-qss-visual-feedback/issues/08-...md`,
`dark-theme-restyle/issues/01-...md`). User provided a logo (dark background, blue crop-frame
icon, "CROPPER" wordmark) and suggested using it to fill the empty gallery space on first load,
instead of - or alongside - the current plain `_EMPTY_STATE_TEXT` message.

Logo saved to `gui/assets/branding/logo.png` (already matches the app's dark theme palette -
same near-black background, blue accent tones).

## User's request

Use the logo to fill the empty-gallery space when the app first loads (no folder processed
yet).

## Not yet decided - open questions for whoever scopes this

- Replace the text message entirely with the logo, or show both (logo above/behind the existing
  "No photos yet..." instructional text)? The current text also serves as an instruction
  ("choose a folder and click Process Folder to get started"), which a logo alone wouldn't
  convey - probably want to keep some instructional text even if the logo is added.
- A logo (fixed-aspect image) sidesteps issue 01's clipped-text bug on its own, but if any text
  remains alongside it, that text still needs issue 01 fixed first, or it'll inherit the same
  clipping risk.
- Sizing: the provided PNG is roughly square, ~1024px - needs scaling down substantially for a
  UI empty-state (existing `_pil_to_pixmap`-style thumbnail scaling exists elsewhere in
  `gui/review_gallery.py` as a pattern to reuse, though that's for photo thumbnails specifically,
  not a static asset).
- Should this logo also become the window/taskbar icon (`QMainWindow.setWindowIcon`), or is this
  ticket scoped to the empty-gallery state only? Worth asking the user if they want it reused
  there too, since window icons are a related but separate use of the same asset.

## Comments
