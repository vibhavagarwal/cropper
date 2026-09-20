# Split emulate() into independent B/W and grain steps

Status: ready

## Context

See `.scratch/bw-grain-filter/spec.md` for the full design and the decisions made during
brainstorming (2026-09-20) — all resolved, don't re-litigate. This ticket is the core pipeline
piece; tickets 02 and 03 thread it through settings/GUI.

## Design (from the spec, section 1)

In `src/hp5_emulate.py`:

1. Factor the existing WB-gain + gray-mix + tone-curve + soften logic out of `emulate()` into a
   `to_bw(img, p)` function. The math is unchanged — this is pure extraction so it can be
   conditionally skipped.
2. `make_grain(h, w, seed, p, size="medium")`: add a `size` multiplier applied to
   `grain_cell`, `grain_amp`, and `grain_fine_amp` together — `small=0.5x`, `medium=1.0x`
   (today's exact constants, must reproduce today's output bit-for-bit at `size="medium"`),
   `large=2.0x`.
3. Generalize grain application from "add to the single luma channel" to "add the same noise
   field to every channel present" — 1 channel for a grayscale array, broadcast across all 3
   channels for an RGB array. This must NOT be independent per-channel noise (that reads as
   color speckling); the identical noise field goes into every channel.
4. New `emulate(img, seed=0, p=PARAMS, apply_bw=True, apply_grain=True, grain_size="medium")`
   is the single entry point covering all 4 combinations:
   - `apply_bw=True, apply_grain=True` → today's HP5 look (must match current output exactly
     when `grain_size="medium"`)
   - `apply_bw=True, apply_grain=False` → flat monochrome, no grain
   - `apply_bw=False, apply_grain=True` → grainy color photo
   - `apply_bw=False, apply_grain=False` → original color, untouched (still goes through the
     function so seed/determinism story stays consistent, but effectively passthrough)
5. Backward compatibility: `emulate(img, seed)` called with just two positional args (as the
   standalone CLI's `process_file`/`render`/`main` do today) must keep behaving exactly as
   before — the new params all default to reproducing today's behavior.

## Testing

TDD in `tests/test_layout_and_filter.py`:
- `emulate(..., apply_bw=True, apply_grain=True, grain_size="medium")` produces the same output
  as today's `emulate(img, seed)` (regression pin — compare pixel arrays or a hash).
- `apply_bw=False` output is NOT grayscale-only (has real per-channel color variance).
- `apply_bw=True, apply_grain=False` output has zero grain-driven pixel variance beyond what
  the tone curve alone produces (e.g. compare two renders of a flat-color input — should be
  identical, since there's no seeded noise to differ).
- `grain_size="small"` vs `"large"` produce measurably different grain amplitude (e.g. std of
  the difference between the raw resized image and the grained output).
- Grain on a color image is the same field across channels — assert the diff between the
  grained and un-grained image is equal (not just correlated) across all 3 channels.

## Out of scope

- No change to `add_border`, `layout`, `center_crop`, or the CLI argument parser in this ticket
  (ticket 03 wires the GUI; the CLI itself is explicitly not required to expose the new flags).
