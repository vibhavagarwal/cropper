# "Running cost" label is a lifetime total, not scoped to the current gallery/run

Status: reported — no fix requested, note only. Unlike issues 01/02, this one was a direct
question ("is it meaningful?") that got a confirmed-by-code answer, not just an observation.

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

## Possible directions (not decided, not implemented)

1. Relabel it honestly — e.g. "Lifetime cost: $X" — cheapest fix, doesn't change behavior, just
   stops it from implying the wrong scope.
2. Scope the displayed number to the current gallery's jobs only (sum `last_cost` over
   `self.cards`, similar to how `_make_job`/per-card cost already works) — matches what the
   label's position visually implies, but changes what information is available at a glance
   (loses the lifetime-spend visibility, which might matter for someone watching total spend
   across a long session of repeated small runs).
3. Show both — e.g. "This run: $X · Lifetime: $Y" — most informative, also the most layout
   space and complexity.

No recommendation made — flagging options for whoever scopes this.

## Notes for whoever picks this up

- Check `.scratch/post-qss-visual-feedback/spec.md` for the full running list before starting.

## Comments
