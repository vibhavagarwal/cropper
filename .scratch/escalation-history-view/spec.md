# In-app view of escalation cost history

Status: requested 2026-09-20, not scoped, not implemented — captured during live testing of a
running build, no investigation or design work done yet.

## Context

User's request, live-testing the app: "I want a log of all the escalations being made and
stored for later reference. Costs money, so better keep track of it."

## What already exists (important — don't rebuild this)

The persistence layer for exactly this already exists and is already in use:

- `DecisionLog` (`src/decision_log.py`) appends a `DecisionRecord` (photo_name, escalated,
  tier, provider, cost, confidence, timestamp) to `~/.cropper/decision_log.jsonl` every time an
  escalation completes (`gui/main_window.py:_on_escalation_done`) — permanently, across every
  app session, never cleared.
- This is already read back in two places: `ReviewGallery.refresh_cost()`
  (`gui/review_gallery.py`) sums *all* records for the lifetime running-cost header (see
  `.scratch/post-qss-visual-feedback/issues/03-...md` — that total's scope is itself a separate
  logged complaint), and `DetailViewDialog` (`gui/detail_view_dialog.py:68-74`) sums cost for
  one specific photo's filename in its info panel.

So "stored for later reference" is already true today — the data survives restarts and is
inspectable by opening `~/.cropper/decision_log.jsonl` directly (it's one JSON object per
line). What's missing is entirely on the *viewing* side.

## The actual gap

No in-app way to browse the escalation history as a list — no table/list view of past
escalations (which photo, when, tier, provider, cost, confidence), no filtering (e.g. by date
range or by folder/run), and no export. The only surfaced views today are a single lifetime sum
and a single photo's total cost, both passive labels, not a browsable log.

## Not yet decided (needs scoping before implementation)

- Where this view lives: a new dialog opened from a button (similar to "Configure API key..."),
  a panel, or something else — not decided.
- Whether it needs filtering/sorting (by date, by folder, by tier) or a flat chronological list
  is enough for v1.
- Whether it needs export (CSV, or just "the underlying file already is one, tell the user
  where it is").
- Whether it should show anything beyond what `DecisionRecord` already captures, or that's
  sufficient.

## Out of scope for now

Implementation. This is a feature request captured during a live-testing session, not a design
or a plan — per this repo's own convention (`CLAUDE.md`), new feature work should be scoped
(likely via brainstorming/grilling) and implemented in its own fresh session, not folded into
whatever session happens to be running when the request comes up.

## Comments
