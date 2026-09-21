# "Running cost" label is a lifetime total, not scoped to the current gallery/run

Status: ready — scoped 2026-09-21

## Observed / confirmed

User asked whether the "Running cost" figure (top-right of the gallery header) is meaningful.
Traced it through the code:

- `ReviewGallery.refresh_cost()` (`gui/review_gallery.py:144-146`) sets the label from
  `self._decision_log.running_cost`.
- `DecisionLog.running_cost` (`src/decision_log.py:38-40`) is `sum(r.cost for r in
  self.records)` — every record ever added to the log, not just ones from the current gallery
  or session.
- `MainWindow.decision_log_path` defaults to `~/.cropper/decision_log.jsonl`
  (`gui/main_window.py:48`), and `DecisionLog.__init__` (`src/decision_log.py:22-30`) loads
  every line from that file on construction — i.e. every escalation ever made in this app,
  across every past session, restart, and "Clear".

So the label is a genuine **lifetime cumulative total**, not "cost of the photos currently
shown," "cost of this run," or "cost since Clear." Positioned directly above the current
gallery grid, it strongly implies scope to what's visible — it isn't. This isn't a vague UX
complaint, it's a confirmed mismatch between what the label appears to mean and what it
actually computes.

## Decision (resolved during scoping, 2026-09-21)

**Show both** — e.g. `"This run: $X · Lifetime: $Y"`.

## Design

- `gui/review_gallery.py`: `ReviewGallery.refresh_cost()` currently sets `cost_label`'s text
  from `self._decision_log.running_cost` alone. Add a "this run" figure computed from the
  gallery's own current cards: sum `getattr(card.job, "last_cost", None) or 0` over
  `self.cards.values()` (same pattern `PhotoCard`'s own per-card cost suffix already uses —
  see `gui/review_gallery.py:99`). Format both into the label, e.g.
  `f"This run: ${this_run_cost:.6f} · Lifetime: ${self._decision_log.running_cost:.6f}"`.
- "This run" should reset naturally on "Clear" / a new "Process Folder" run since it derives
  from `self.cards`, which `clear()` already empties — no separate tracking needed.
- Consider whether the `#costLabel` QSS selector/styling still reads well with the longer text;
  probably fine, but worth a visual check once implemented.

## Testing

- `ReviewGallery.refresh_cost()` test: gallery with some cards having `last_cost` set and a
  `DecisionLog` with unrelated historical records — assert the label contains both the
  gallery-scoped sum and the full lifetime sum, and that they differ when they should (i.e. the
  test needs to prove they're computed independently, not just that both numbers appear
  somewhere).
- Existing tests asserting on `cost_label`'s exact text format will need updating for the new
  two-part format.

## Comments
