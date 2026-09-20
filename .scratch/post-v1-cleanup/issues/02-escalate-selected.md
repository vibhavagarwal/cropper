# Escalate selected photos (batch action)

Status: ready

## Context

The original spec (`.scratch/desktop-tool/spec.md` line ~48) called for an "escalate all
flagged" batch action alongside the per-photo escalate button. During grilling
(2026-09-20) the user rejected the "all flagged" framing outright — they want precise,
opt-in control over which specific flagged photos get escalated, not a blanket action. This
ticket implements that instead of the spec's original "all flagged" wording.

## Design

- **Selection mechanism**: a second per-card checkbox (distinct from the existing "Keep"
  checkbox — separate concerns, both visible on the card), labeled for escalation selection.
  Enabled only on cards that are eligible: `job.triage_decision.escalate` is true **and**
  `job.crop_decision` is not already set (mirrors the existing enablement check the single
  "Escalate" button in `PhotoCard` uses at `gui/review_gallery.py:34`, plus excluding
  already-escalated jobs so the batch action can't accidentally re-spend on a photo that
  already has a decision).
- **Trigger**: a new "Escalate selected" button in the bottom action row
  (`gui/main_window.py`, alongside Save Selected / Choose output folder... / Clear), enabled
  only when at least one photo is currently selected for escalation.
- **Cost confirmation**: reuse `EscalationConfirmDialog` (`gui/escalation_dialog.py`), scoped
  to just the selected set (`num_photos=len(selected)`), same worst-case-cost-estimate pattern
  the single-photo path already uses.
- **Processing**: sequential, reusing the existing per-photo escalation path
  (`_run_escalation_worker`, including the automatic cheap→strong follow-up on low confidence).
  This means the GUI blocks for the duration of the whole batch — same known tradeoff as
  today's single-photo path (see tech debt item 6 in `.scratch/post-v1-cleanup/spec.md`,
  explicitly left parked this round), just compounded across N photos. Not addressed here;
  the light busy indicator from `01-ui-ux-cleanup.md` at least makes it visibly "in progress"
  rather than silently frozen.
- **Partial failure handling**: on a per-photo error mid-batch, skip that photo and continue
  processing the rest, then report a summary at the end — e.g. "Escalated 4 of 5 — 1 failed:
  <filename>." Mirrors the existing partial-success pattern in `_on_save_clicked`
  ("Saved N of M... failed").

## Out of scope

- Fixing the GUI-blocking-thread tech debt (item 6 in the handoff spec) — explicitly parked.
- Any change to per-photo escalation eligibility rules beyond what's stated above.
