# Empty-state gallery placeholder box is still too big

Status: reported 2026-09-21, not scoped, not implemented — note-taking only.

## Context

Follow-up to issue 01 (`01-first-load-layout-spacing-off.md`), which gave the gallery explicit
stretch priority in `MainWindow`'s central layout so it fills available vertical space instead
of the "Run settings" box. That fix landed and works as intended - but it means the *consequence*
of an empty gallery is now more visible: the dashed empty-state box
(`#emptyState` in `gui/main.py`, the `ReviewGallery.empty_label` widget shown when there are no
cards) stretches to fill that same space, and on a first run with no folder processed yet, that
leaves a very large, mostly-empty dashed rectangle dominating the window - see the user's
screenshot, taken right after the layout fix, with the empty-state box circled as still feeling
oversized.

## User's request

None yet - explicitly flagged as "no changes for now," just capture for later.

## Notes for whoever picks this up

- Check `.scratch/post-qss-visual-feedback/spec.md` for the full running list before starting.
- Likely candidates once scoped: cap the empty-state box's own height/stretch independent of the
  gallery's (so it doesn't inherit the gallery's full stretch=1 allocation when there are no
  cards), or reduce its `padding` in the QSS (`gui/main.py`'s `#emptyState` rule currently uses
  `padding: 48px`).
- Not investigated further - no code changes attempted, this is a live-testing observation only.

## Comments
