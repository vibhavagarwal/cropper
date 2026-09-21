# Gallery grid leaves large empty space on the right side of wide windows

Status: reported — no fix requested, note + suggestions only, per explicit "no changes though"

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

No recommendation made here — flagging the options and the prior-decision tension for whoever
scopes this, not picking one.

## Notes for whoever picks this up

- User said explicitly: no changes right now.
- Check `.scratch/post-qss-visual-feedback/spec.md` for the full running list before starting —
  more items from the same live-testing session may have been added after this one.

## Comments
