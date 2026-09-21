# Gallery grid leaves large empty space on the right side of wide windows

Status: ready — deliberately reverses the prior "not a pain point" decision (see below), scoped
2026-09-21

## Observed

Screenshot after processing a folder of 8 photos. The gallery grid is fixed at 4 columns with a
capped thumbnail size (`gui/review_gallery.py`, confirmed via code: `#photoCard { min-width:
248px; max-width: 248px; }` in the QSS, and the grid itself doesn't appear to reflow column
count based on width). On a wide window, the 4 columns of cards occupy roughly the left third
to left half of the available width, leaving a large blank area to the right — most visible
with fewer than 8 photos (only one row) but present in the two-row case shown too.

## Tension with a prior explicit decision

This directly revisits something already decided once: `.scratch/post-v1-cleanup/issues/
01-ui-ux-cleanup.md` states "Gallery grid (fixed 4-columns-per-row, 220px thumbnail cap...)
... confirmed **not** a pain point, leave alone" — decided during grilling before the QSS pass
existed. Worth surfacing that this is a live re-litigation of that call, not a fresh complaint,
in case that context changes the answer.

## Possible directions (not decided, not implemented — user asked for suggestions only)

1. **Make the grid responsive** — compute column count from the gallery's available width at
   layout time instead of a hardcoded 4, so cards reflow to fill the window. Most direct fix
   for the empty-space complaint, but is exactly the change the prior decision above explicitly
   ruled out — would need to be a deliberate reversal, not a quiet change.
2. **Increase the thumbnail/card size** instead of changing column count — bigger cards fill
   more width without touching the grid's reflow logic. Simpler, lower risk, but doesn't scale
   well to very wide windows (still hits a ceiling) and changes the density of what's visible
   at once.
3. **Constrain the window/gallery width** rather than the grid — cap the main window's default
   or maximum width closer to what 4 fixed-size columns actually need, so the empty space
   doesn't appear rather than making the grid fill it. Cheapest change, but caps how much the
   user can resize the window usefully, and doesn't help if they still stretch it wide.
4. **Center the grid** within the available gallery width instead of left-anchoring it — doesn't
   remove the empty space but distributes it symmetrically instead of dumping it all on the
   right, which may read as less obviously "broken" even though the underlying density issue is
   unchanged.

## Decision (resolved during scoping, 2026-09-21)

**Option 1 — make the grid responsive.** Explicit, deliberate reversal of the prior
`post-v1-cleanup` call, confirmed by the user. Column count should be computed from the
gallery's available width at layout time instead of the hardcoded 4, so cards reflow to fill
the window.

## Design

- `gui/review_gallery.py`: `ReviewGallery._grid` (a `QGridLayout`) currently gets cards placed
  via `divmod(self._next_index, 4)` (hardcoded 4 columns) in `add_job`. Replace with a column
  count derived from the scroll area's available width divided by the card width (248px,
  matching the QSS `#photoCard` min/max-width) plus spacing — recompute on resize, not just at
  add-time, so an existing gallery reflows if the user resizes the window after processing a
  folder (not just on the next `add_job` call). This likely means overriding `resizeEvent` on
  `ReviewGallery` or its scroll area, and re-laying-out existing cards into the grid at the new
  column count rather than only placing new ones.
- Keep the 248px card width and existing QSS untouched — only the column-count/placement logic
  changes, not card sizing.

## Testing

- Unit test: given a gallery width wide enough for N columns, adding M cards places them at the
  expected `(row, col)` positions for that column count (verifies the width→column-count
  calculation, not actual pixel rendering).
- Unit test: reflow on resize — add cards at one width, simulate a resize to a wider width,
  assert card positions update to use more columns (not just that new cards would use them).
- Existing gallery tests (`ReviewGalleryTests` in `tests/test_gui_smoke.py`) that assume a fixed
  4-column layout will need updating to either fix the test width or assert relatively.

## Comments
