# In-app view of escalation cost history

Status: scoped 2026-09-21, broken into one implementation-ready ticket under
`.scratch/escalation-history-view/issues/`: `01-history-dialog.md`.

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

## Decisions (resolved during scoping, 2026-09-21)

- **A new dialog**, opened via a new button in the bottom row (alongside "Configure API key...").
- **Flat chronological list, newest first, for v1** — no filtering/sorting/export. Shows exactly
  what `DecisionRecord` already captures (photo, date/time, tier, provider, cost, confidence) —
  nothing beyond that for v1.
- Filtering/sorting and export were both explicitly considered and deferred, not forgotten —
  see the ticket for how to leave room for them later without over-building now.

## Out of scope for v1

Filtering, sorting, export, and anything beyond what `DecisionRecord` already stores. Explicitly
deferred, not rejected — a future ticket if it turns out to matter in practice.

## Comments
