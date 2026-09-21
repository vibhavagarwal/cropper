# "Flagged for escalation" messaging is only meaningful once triage thresholds are tuned

Status: resolved via a separate ticket — see
`.scratch/triage-and-border-tuning/issues/01-remove-saliency-edge-touch-from-triage.md`, which
was scoped 2026-09-21 to remove the saliency edge-touch check entirely (the specific condition
diagnosed below as the most likely over-triggering culprit). No separate fix needed here — this
file remains as the diagnosis/context that motivated that ticket.

## Observed / discussion

User asked why every photo in a test folder was showing "flagged for escalation." Traced to
`src/triage.py`'s `THRESHOLDS` — explicitly documented as "initial guesses... tune them against
labeled real batches, not eyeballed" — and specifically the saliency edge-touch check
(`src/detection.py:55-69`), which flags `touches_edge=True` if even a single pixel in a thin
3%-of-long-edge border band is above the saliency threshold. Real, frame-filling photos (street
scenes, storefronts, close-ups) trip this very easily, so with current defaults nearly
everything escalates.

User's follow-up observation: if the "flagged for escalation" badge fires on nearly every
photo, it stops being a meaningful signal — a badge that's (almost) always present tells you
nothing you couldn't already assume by default. This isn't a claim that the messaging itself is
wrong, just that it's currently drowned out by miscalibrated thresholds.

## Conclusion (not a fix, just the framing for later)

The messaging is fine in principle and should become genuinely useful once the thresholds are
tuned against real labeled batches (already a documented open item — see `triage.py`'s
docstring and `docs/pipeline-brief.md` open item #1). This ticket exists so that whoever tunes
those thresholds knows the badge-noise complaint is really a symptom of that, not a separate
UI problem to solve on its own.

## Notes for whoever picks this up

- Check `.scratch/post-qss-visual-feedback/spec.md` for the full running list before starting.
- No fix scoped here — this is context for whoever eventually does the threshold-tuning work
  (`docs/pipeline-brief.md` open item #1), not a standalone ticket to implement.

## Comments
