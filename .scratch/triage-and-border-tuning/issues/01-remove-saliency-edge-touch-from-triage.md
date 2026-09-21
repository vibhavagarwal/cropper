# Remove the "saliency blob touches an edge or corner" check from escalation triage

Status: ready — scoped 2026-09-21

## Context

Follow-up to `.scratch/post-qss-visual-feedback/issues/04-escalation-flag-messaging-is-noise-until-thresholds-tuned.md`,
where it was traced that the edge-touch check (`src/detection.py:55-69`'s `touches_edge`, fed
into `src/triage.py:27-28`) trips on almost every real photo, since it fires if even a single
pixel in a thin 3%-of-long-edge border band is above the saliency threshold. Frame-filling
travel photos (storefronts, street scenes, close-ups) hit this constantly, making the
"flagged for escalation" badge close to meaningless with current defaults.

## User's request

Remove this specific check (`"saliency blob touches an edge or corner"`, `src/triage.py:27-28`)
from the triage gate entirely, rather than trying to retune its threshold. The other three
triage conditions (saliency spans ~whole frame, multiple faces with no clear primary, ambiguous
symmetry score) would remain.

## Decision (resolved during scoping, 2026-09-21)

**Remove the check entirely**, confirmed as originally requested (not narrowed/retuned). The
other three triage conditions (saliency spans ~whole frame, multiple faces with no clear
primary, ambiguous symmetry score) are unaffected.

## Design

- `src/triage.py`: delete the `if detection.saliency.touches_edge:` block (lines 27-28) from
  `triage()`, including its `"saliency blob touches an edge or corner"` reason string.
- `src/detection.py`: `SaliencyResult.touches_edge` and its computation in `saliency_map()`
  become unused outside `detection.py` itself once this lands (confirmed: `touches_edge` is
  currently referenced only at `src/triage.py:27` outside its own module). Recommend **leaving
  the field and its computation in place** — it's cheap, keeps `detection.py`'s public shape
  stable, and remains available if a future triage revision wants it back — rather than ripping
  it out of `detection.py` too. Flagging this as a call the implementer should confirm rather
  than assuming.

## Testing

- `tests/test_triage.py`: has a `make_detection(touches_edge=True)` case (around line 46)
  asserting `"saliency blob touches an edge or corner" in decision.reasons` — this specific
  test must be removed or repurposed (e.g. assert `touches_edge=True` alone no longer causes
  escalation, to positively confirm the removal rather than just deleting the old assertion).
- `tests/test_detection.py`'s `test_whole_frame_bright_blob_touches_edge` tests
  `detection.py`'s own `touches_edge` computation directly, not triage — no change needed there
  if the field itself is kept (per the Design note above).
- Add/update a triage-level test confirming a detection with `touches_edge=True` and every
  other condition false does *not* escalate (currently would, per `test_triage.py`'s existing
  case) — this is the actual behavior-change regression test, not just removing old assertions.

## Comments
