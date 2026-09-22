# Dark theme regressions: mismatched label "chip" backgrounds, clipped empty-state text

Status: fixed 2026-09-21. `QLabel { background: transparent; }` added to `gui/main.py`'s
stylesheet (per the user's explicit direction). `gui/review_gallery.py`'s `empty_label` now uses
`setFixedWidth(_EMPTY_STATE_WIDTH)` + `QSizePolicy.Fixed/Preferred` instead of relying on
`AlignHCenter` alone, so word-wrap height-for-width sizing is deterministic. Verified with a new
regression test (`test_empty_label_is_not_clipped_at_wide_window_widths`) and a visual check at
the same ~1270px width from the original screenshot.

## Observed

User's screenshot (Run settings box + empty gallery) circles two problems:

1. **"Shape:", "Canvas long edge:", "Grain size:", "Border size:" labels each show a visible
   mismatched dark rectangle behind their text**, distinct from the "Run settings" panel's own
   background - reads as a rendering glitch/chip rather than blended text.
2. **The "No photos yet..." empty-state message is clipped** - only shows "No photos yet —
   choose a folder and click Process Folder to get" with the rest of the sentence
   ("started.") cut off below the box's visible bottom edge.

## Root cause 1: label chip backgrounds (confirmed by re-reading `gui/main.py`)

```css
QMainWindow, QDialog, QWidget { background: #16191d; color: #f0f3f6; ... }
```

Including bare `QWidget` in this selector means every widget - including every `QLabel` - paints
its own solid `#16191d` background behind its text. That's invisible on the plain window
background, but wherever a label sits on a differently-colored container (the `#21262d` "Run
settings" `QGroupBox`, the `#21262d` `#emptyState` box, `#21262d` `#photoCard`), the label's own
background patch shows through as a mismatched rectangle.

The **original light theme** scoped this rule to `QMainWindow, QDialog` only (not `QWidget`),
which avoided the problem entirely - labels had no explicit background, so they transparently
took on whatever was behind them. The dark restyle broadened the selector to `QWidget` in order
to get `color: #f0f3f6` applied everywhere, and picked up the background side effect without it
being noticed.

**Fix direction (user's explicit preference, 2026-09-21)**: rather than re-scoping the
`background` rule off of `QWidget` generally, add an explicit `QLabel { background: transparent; }`
rule - labels specifically should never paint their own background, full stop, regardless of
what other selectors exist. Simpler and more direct than threading the light theme's
`QMainWindow, QDialog`-only scoping back in, and forecloses the same chip bug recurring if
another broad `QWidget` background rule gets added later.

## Root cause 2: clipped empty-state text (confirmed by re-reading `gui/review_gallery.py`)

The issue-08 centering fix wraps `empty_label` in a wrapper layout with
`empty_wrapper_layout.addWidget(self.empty_label, alignment=Qt.AlignHCenter)`. The
`Qt.AlignHCenter` flag makes the word-wrapped label size itself to Qt's own "preferred width"
heuristic instead of the container's full available width - so at this window width it wraps to
more, narrower lines than before the centering fix, and the label's height (already constrained
to `QSizePolicy.Maximum`, i.e. its own `sizeHint`) doesn't get recalculated correctly against
that narrower wrap width, clipping the last line.

**Likely fix**: give `empty_label` an explicit fixed/minimum width before wrapping (e.g. based on
a chosen character width or a fraction of the gallery's width) rather than letting `AlignHCenter`
pick an unconstrained "preferred" width, or center the wrapper's *contents area* without relying
on `AlignHCenter`'s width-shrinking behavior (e.g. size the label to a fixed width and center
that fixed-width block instead).

## Comments
