# Empty gallery still leaves a large blank void, even after the dashed-box fix

Status: reported 2026-09-21, not scoped, not implemented — note-taking only.

## Context

Follow-up to issue 05 (`05-empty-gallery-placeholder-too-large.md`), which fixed the dashed
`#emptyState` box itself stretching to fill available height (gave `cost_label`/`empty_label`
`Maximum` vertical size policy, gave `_scroll` explicit `stretch=1` in `ReviewGallery`'s own
layout). That fix landed and works as intended for the box itself.

User's new screenshot shows the actual complaint wasn't fully resolved: with the box now
compact, there's still a large blank gap between it and the bottom button row - just without a
border around it now. See the user's circled screenshot.

## Root cause (this time actually the full picture, not just the box)

`gui/main_window.py`'s central `QVBoxLayout` gives `self.gallery` (the whole `ReviewGallery`
widget) `stretch=1` - from the very first layout ticket
(`.scratch/post-qss-visual-feedback/issues/01-first-load-layout-spacing-off.md`), specifically
so a *populated* gallery isn't squeezed below the "Run settings" box. That stretch factor is
unconditional - it applies whether or not the gallery has any cards. Issue 05's fix only stopped
the box *inside* the gallery from claiming that reserved space; the gallery widget itself still
reserves it every time, empty or not. So the fix moved the void from "inside a stretched dashed
box" to "blank space below a compact box, inside a still-stretched gallery widget" - visually
smaller-looking box, same total wasted area.

## Tension with issue 01's decision

Issue 01 deliberately made the gallery's stretch unconditional ("arguably the most important
part of the window ... should grow") without carving out an empty-state exception. Fixing this
properly means either making that stretch conditional (collapse when empty, expand once
populated) or accepting a different tradeoff - worth flagging as a genuine revisit of that
decision, not an oversight to just patch.

## Not yet decided - open questions for whoever scopes this

- Toggle the gallery's stretch factor dynamically (`stretch=0` when `len(self.cards) == 0`,
  `stretch=1` once populated) - most direct fix, but stretch factors on an already-added layout
  item aren't trivially changeable in Qt; likely means removing/re-adding the widget to the
  layout, or restructuring how MainWindow's central layout is built.
- Alternative: keep the gallery's stretch as-is, but vertically center the empty-state message
  within the gallery's available space instead of top-anchoring it - doesn't shrink the void but
  distributes it around the message instead of dumping it all below, same kind of tradeoff as
  the gallery-grid centering option that was considered (and not chosen) in issue 02.

## Comments
