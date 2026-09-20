# Thread apply_bw / apply_grain / grain_size through settings, PhotoJob, and render_photo

Status: ready

## Context

Depends on ticket 01 (the new `emulate()` signature must exist first). See
`.scratch/bw-grain-filter/spec.md` section 2 for the full design.

## Design

- `src/settings.py`: `AppSettings` replaces `apply_filter: bool = True` with three fields:
  `apply_bw: bool = True`, `apply_grain: bool = True`, `grain_size: str = "medium"`. The
  loader already ignores unknown fields (see `test_load_ignores_unknown_fields_gracefully`),
  so an old settings.json with a stale `apply_filter` key must still load cleanly with the new
  defaults — don't add special migration logic for it.
- `src/pipeline.py`: `PhotoJob` replaces its `apply_filter: bool` field with the same three
  fields. Thread them through `process_photo`, `process_folder`, `apply_escalation`,
  `apply_manual_crop`, and `render_photo` (signature changes only — no new logic beyond calling
  the new `emulate()` from ticket 01).
- `render_photo` picks the canvas mode from `apply_bw`: `"L"` (grayscale) when `apply_bw=True`,
  `"RGB"` when `apply_bw=False`. The border-paste logic already handles either mode via PIL, but
  verify the white border value works for both (`255` for `"L"`, needs `(255, 255, 255)` for
  `"RGB"` — check `Image.new(mode, size, value)`'s handling of mode-appropriate fill values).

## Testing

TDD, updating rather than leaving behind:
- `tests/test_settings.py`: round-trip and default-value tests for the three new fields
  (replacing/extending whatever currently covers `apply_filter`).
- `tests/test_pipeline.py`: `process_photo`/`process_folder`/`apply_escalation`/
  `apply_manual_crop` tests that currently pass `apply_filter=True/False` need updating to the
  three-field signature; add cases confirming `render_photo` produces an `"RGB"`-mode canvas
  when `apply_bw=False` and `"L"`-mode when `apply_bw=True`.

## Out of scope

- GUI wiring (ticket 03).
- No retroactive migration of old `apply_filter` values beyond the loader's existing
  graceful-default behavior (explicitly decided in the spec).
