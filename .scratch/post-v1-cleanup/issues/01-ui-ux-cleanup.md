# UI/UX cleanup pass

Status: ready

## Context

Grilled from the open scope in `.scratch/post-v1-cleanup/spec.md` section 1 ("an extensive
UI cleanup - its functional but not pretty and easy to use"). All decisions below were
confirmed with the user in the grilling session on 2026-09-20.

## Scope boundary

- Cosmetic/UX only: styling, spacing, and layout of screens/controls that already exist.
- Explicitly **not** in scope: toolbar, menu bar, keyboard shortcuts, or any other
  structural addition. (The API key work in `03-api-key-keyring.md` deliberately avoids a
  menu bar for this same reason — see that ticket.)
- Styling direction: generic usability heuristics (consistent spacing, clear primary/secondary
  hierarchy, grouped controls) — not a named design language (no Fluent/Material adoption).
- Light-only. Dark mode is out of scope for this pass.
- Gallery grid (fixed 4-columns-per-row, 220px thumbnail cap in `review_gallery.py`) and
  window sizing/resizing behavior: confirmed **not** pain points, leave alone. (A sensible
  minimum window size can be added as a trivial safety net alongside the other layout changes,
  but doesn't need its own design work.)

## Confirmed changes

1. **Input panel** (`gui/input_panel.py`): group the run-settings cluster (Shape / Canvas long
   edge / Apply HP5 filter) visually apart from the folder picker, and give "Process Folder"
   primary-action visual weight versus secondary controls like "Browse...".

2. **Confirm-before-clear on re-run**: `MainWindow._start_processing` (`gui/main_window.py:98`)
   currently calls `self.gallery.clear()` unconditionally. Add a confirmation dialog, but only
   when the gallery has unsaved kept work (jobs that would be discarded) — an empty gallery, or
   one where everything's already been saved, should proceed silently with no prompt.

3. **Remove `CostPanel` as a standalone widget** (`gui/cost_panel.py`, wired in
   `main_window.py`): eliminate the separate section entirely.
   - Running total moves into a small header built into `ReviewGallery` itself
     (`gui/review_gallery.py`), pinned above the grid.
   - Per-photo cost history moves into the existing `DetailViewDialog`
     (`gui/detail_view_dialog.py`) as one more info line alongside tier/confidence — it already
     opens per-card from the gallery's "Details" button.
   - Additionally: append cost inline to each `PhotoCard`'s status text for escalated photos
     (e.g. `"escalated (cheap, confidence 0.82, $0.000123)"`) so cost is visible at a glance in
     the gallery, not just in Details. Non-escalated cards ("formula crop") show no cost — there
     isn't one.

4. **Empty-state message**: when the gallery has no jobs (first run, or after Save Selected/
   Clear empties it), show a placeholder instead of a blank `QScrollArea` — e.g. "No photos yet
   — choose a folder and click Process Folder to get started."

5. **Light busy indicator**: a simple indeterminate spinner/progress bar shown during folder
   processing (`_start_processing`) and escalation calls (`_run_escalation_worker`), replacing
   "nothing visibly happens" with "something is happening." Explicitly not full N-of-M progress
   tracking — that would need `ProcessFolderWorker`/`EscalationWorker` to report counts, which
   is out of scope here.

## Confirmed out of scope

- Dark mode.
- Gallery grid responsiveness / thumbnail size changes.
- Window sizing/resizing behavior changes (beyond a trivial sensible-minimum-size safety net).
- Toolbar, menus, keyboard shortcuts, or any other structural change.
- Full N-of-M progress bars (light indeterminate indicator only).

## Reference

A visual mockup of the redesigned layout (grouped input panel, primary/secondary button
hierarchy, gallery header with running cost + empty state, per-card cost line) was shown to and
approved by the user during grilling — see session transcript, 2026-09-20.
