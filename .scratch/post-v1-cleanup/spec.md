# Post-v1 cleanup: UI/UX pass + remaining spec gaps

Status: grilled 2026-09-20. Resolved into implementation-ready tickets under
`.scratch/post-v1-cleanup/issues/`:
- `01-ui-ux-cleanup.md` — section 1, full scope resolved
- `02-escalate-selected.md` — section 2 item 1 (spec's "escalate all flagged" reworked to
  "escalate selected" per user's explicit correction during grilling)
- `03-api-key-keyring.md` — section 2 item 2

Section 2 items 3-8 (deferred features + tech debt, see below) were explicitly triaged as
**out of scope** for this round and left parked — not re-litigated, just confirmed still
correct. This file remains the historical record of what was open before grilling; the issue
files are the source of truth for what to build.

## Context

Cropper's v1 (21-task implementation plan, see `docs/superpowers/plans/2026-09-20-desktop-tool.md`)
is built, reviewed, and merged to `master`. The original requirements are in
`.scratch/desktop-tool/spec.md` — that document is still the source of truth for what v1 was
supposed to do; this file only covers what's left after it shipped.

Since merge, a few small bug-fixes and features landed directly (each with tests, TDD, committed
to `master` — no need to re-litigate these in the grilling session, they're done):
- A "Clear" button on the review gallery (manual reset).
- Manual crop dialog now shows a status-bar message on both accept and cancel (previously gave
  no feedback either way, which looked like "nothing happened" on a successful crop).
- `Process Folder` now clears the review gallery before starting a new run, instead of
  accumulating cards from every past run.
- `Save Selected` now removes saved photos from the gallery view, leaving only what wasn't
  saved.

Two things are open and are what this handoff is for:

## 1. UI/UX cleanup (undefined scope — start here)

The user's own words: **"an extensive UI cleanup - its functional but not pretty and easy to
use."** Nothing more specific has been pinned down yet. This was classified as a **bounded**
task (improving existing screens, not restructuring the app), but scoping stalled: a
multiple-choice question about pain points (dated look / cramped gallery / unclear controls / no
progress feedback) was dismissed unanswered, and a follow-up open-ended question was asked but
not yet answered before the user asked to defer this to a dedicated session instead.

**Start the grilling session on this topic.** Some concrete starting branches for the design
tree (not exhaustive — this is exactly what grilling should surface):
- What "pretty" means here: a QSS stylesheet pass (color, spacing, typography, rounded corners,
  hover states)? Dark mode? Just tidier default-Qt spacing/margins?
- What "easy to use" means concretely: is the friction from unlabeled/ambiguous controls,
  from the gallery grid being cramped (thumbnails are capped at 220px, see
  `gui/review_gallery.py:_pil_to_pixmap`), from a lack of progress feedback during a folder
  run or an escalation call (currently only a status-bar text message, no progress bar/spinner),
  or from window sizing/resizing behavior?
- Whether this is a visual-only pass (styling, spacing, iconography) or also touches layout/flow
  (e.g. grouping input controls, reordering the gallery/cost-panel/save-row relationship,
  adding empty-state messaging when no folder has been processed yet).
- Whether the review gallery's fixed 4-columns-per-row grid (`gui/review_gallery.py:add_job`,
  `divmod(self._next_index, 4)`) should become responsive to window width instead of fixed.
- Scope boundary: is this purely cosmetic/UX, or does the user also want structural changes
  (e.g. a toolbar instead of button rows, menus, keyboard shortcuts)?

The **visual companion** (browser-based mockup tool available to the brainstorming skill) is
worth offering once a real layout/mockup question comes up — this is exactly the kind of
question that's clearer shown than described.

## 2. Remaining enhancements (verified against `.scratch/desktop-tool/spec.md` and the actual code, 2026-09-20)

These are independent of the UI cleanup above and can be grilled/prioritized separately or
folded into the same session.

**Spec-required but never built:**
1. **"Escalate all flagged" batch action** — spec (`.scratch/desktop-tool/spec.md` line ~48)
   requires this alongside per-photo escalation; only the per-photo "Escalate" button
   (`gui/review_gallery.py:PhotoCard`) exists. Never allocated to a task during planning; flagged
   but not scheduled during the final whole-branch review.
2. **In-app API key field with OS-keyring storage** — spec requires it; `keyring` is in
   `requirements.txt` completely unused (`grep -rn keyring src/ gui/` returns nothing). Today the
   only way in is the `OPENAI_API_KEY` environment variable, checked in
   `gui/main_window.py:MainWindow.__init__`.

**Explicitly deferred in the spec (not gaps — intentionally "later"):**
3. **Portrait theme filter + automatic theme classification** — the landscape HP5 filter applies
   to every photo regardless of theme (`src/pipeline.py:render_photo` always calls
   `H.emulate`). Spec section "Filter step" defers this.
4. **OpenAI Batch API mode** (50% cost discount on escalation) — spec section "Escalation / AI
   crop decision" calls this "a later optimization, not built now."
5. **Additional AI providers** (Anthropic, Grok) — `src/providers/base.py`'s `CropProvider` ABC
   is provider-agnostic by design; only `src/providers/openai_provider.py` implements it.

**Known technical debt (deliberately parked during the build, not forgotten):**
6. Escalation calls block the GUI thread — `gui/main_window.py:_run_escalation_worker` does
   `start()` then `wait()` synchronously, freezing the window for each API call including the
   automatic cheap→strong follow-up. A prior review ruling flagged that removing the blocking
   `wait()` later requires first holding a live reference to the worker (see git history on
   `gui/main_window.py` around the `escalation_worker` local var) — otherwise it reintroduces the
   exact crash class fixed as the final review's Critical #1.
7. Escalation sends the full-resolution source image over the network instead of a downscaled
   proxy (`src/pipeline.py:apply_escalation`) — `src/cost.py`'s own comment assumes a downscaled
   proxy when estimating tokens, so real cost/latency is worse than the estimate shown in
   `gui/escalation_dialog.py`.
8. Two regression tests added in the last fix wave are thinner than ideal: the manual-crop
   non-degenerate-geometry test (`tests/test_gui_smoke.py:CropEditorDialogTests
   .test_manual_crop_uses_correct_ratio_for_non_square_source`) uses a 1.0 target ratio and
   never exercises the full `apply_manual_crop` round-trip; the overlay test
   (`DetectionOverlayTests.test_overlay_is_same_size_as_source_and_marks_a_face`) is a smoke
   assertion that would have passed under the old, buggy geometry too. The underlying fixes were
   verified correct by hand at the time — this is a test-coverage gap, not a suspected bug.

**Cosmetic (low priority, likely not worth a grilling round):** missing type hints across
several `src/`/`gui/` modules, a repeated `sys.path.insert` pattern copied across 5 `gui/` files,
a slightly-misnamed `actual_cost` variable in `gui/main_window.py:_on_escalation_done`.

## Environment / repo state (for orientation, not something to re-decide)

- `master` is clean, single branch, no stray worktrees. `.venv/` exists with pinned
  `requirements.txt` versions installed and verified (test suite green from inside it).
- Full test suite: `python -m unittest discover -s tests -v` — 93/93 passing as of this handoff.
- `~/.cropper/decision_log.jsonl` was cleared of stale test-residue entries; it's a real runtime
  log file (not a git-tracked one) that accumulates as the app is actually used.
