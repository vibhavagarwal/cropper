# "Symmetry score is ambiguous" triage condition may be over-firing, same shape as the edge-touch issue

Status: requested 2026-09-21, not scoped

## Context

User asked what "symmetry score is ambiguous" (an escalation reason) means, live-testing after
the face-detection DNN swap (`issues/01-...md`) confirmed working. Explained: `symmetry_score()`
(`src/detection.py`) flips the photo left-right and compares it to the original - near 1.0 means
highly mirror-symmetric, near 0 means clearly asymmetric. `triage.py`'s `THRESHOLDS` flags it
"ambiguous" when the score falls between `symmetry_ambiguous_low=0.55` and
`symmetry_ambiguous_high=0.80`.

## User's concern

Wants this revisited - same underlying issue as the edge-touch check that was already removed
(`.scratch/triage-and-border-tuning/issues/01-remove-saliency-edge-touch-from-triage.md`):
`THRESHOLDS` is explicitly documented in `triage.py` as "initial guesses... tune them against
labeled real batches, not eyeballed," and a 0.55-0.80 band is fairly wide - plausibly firing on
a large fraction of ordinary photos the same way the edge-touch check did, making the triage
badge noisy/uninformative again.

## Not yet investigated / open questions for whoever scopes this

- Unlike the edge-touch check, no concrete evidence yet that this specific condition is
  over-firing in practice (that was confirmed empirically for edge-touch by testing real
  photos) - this is a user hypothesis based on the band's width and the thresholds' documented
  "not tuned" status, not a confirmed measurement. Worth checking against a batch of real
  photos before deciding whether to retune vs. remove vs. leave alone.
- If retuning: narrow the band (raise the low threshold and/or lower the high threshold) rather
  than removing the check entirely, unless a real-batch check shows it's similarly
  near-meaningless across the board the way edge-touch was.
- Relatedly: `src/pipeline.py`'s `process_photo` derives `symmetric` (whether `formula_crop`
  centers the subject vs. thirds-places it) from `symmetry_score >= THRESHOLDS["symmetry_ambiguous_high"]`
  (i.e. only the *upper* threshold, not the ambiguous band) - so retuning the ambiguous band's
  thresholds would also shift what counts as "symmetric enough to center" for the formula-crop
  path, not just the escalation trigger. Worth confirming that's an acceptable side effect or
  whether the two uses need to be decoupled into separate thresholds.

## Comments
