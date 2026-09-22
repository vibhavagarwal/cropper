# Per-card Escalate button never re-enables after a preview card is upgraded

Status: logged — found 2026-09-21, not yet triaged

## Context

Found while building an automated GUI demo-recording script that drives the real app (Load
Folder, then Process Folder on the same folder, so preview cards get upgraded in place rather
than rebuilt). Not found through deliberate testing of this code path.

## Symptom

In `gui/review_gallery.py`, `PhotoCard.__init__` sets the per-card "Escalate" push button's
enabled state once, at construction:

```python
escalate_button = QPushButton("Escalate")
escalate_button.setEnabled(_escalation_eligible(job))
```

That button is a local variable, never stored as `self.escalate_button`. When a card is created
from a folder-preview job (`processed=False`, `triage_decision=None`, so `_escalation_eligible`
is `False`) and later upgraded to the real processed job via `PhotoCard.update_job()` ->
`_refresh_visuals()`, `_refresh_visuals()` re-enables `self.escalate_checkbox` based on the new
job's eligibility, but has no reference to the push button to do the same for it:

```python
def _refresh_visuals(self):
    eligible = _escalation_eligible(self.job)
    self.escalate_checkbox.setEnabled(eligible)
    ...
```

Net effect: a photo that gets flagged for escalation after Process Folder runs (status label
correctly shows "flagged for escalation") still has a permanently disabled "Escalate" button,
if that card started life as a preview card for the same folder. The "Select for escalation"
checkbox + the bottom "Escalate selected" button are unaffected (that path was used as a
workaround for the demo recording).

This does not reproduce when Process Folder is the first thing run against a folder that was
never previewed first (fresh cards are created with the correct, already-eligible job, so the
button is enabled from the start) — only the preview-then-process upgrade path is affected.

## Suggested fix (not yet decided on)

Store the button as `self.escalate_button` and add `self.escalate_button.setEnabled(eligible)`
alongside the existing checkbox line in `_refresh_visuals()`. Would want a test that creates a
preview card, upgrades it via `update_job()` to a job flagged for escalation, and asserts the
button is enabled — mirroring how `_escalation_eligible` is already exercised elsewhere.

## Comments
