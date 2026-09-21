# B/W filter unchecked, but saved output is still black and white

Status: fixed (commit 5b117d2) — see "Session update" below

## Observed

User unchecked "Apply B/W filter" in the input panel before processing a folder, then saved
the kept photos. The saved output was black and white, not color.

## Expected (per `.scratch/bw-grain-filter/spec.md`)

Unchecking "Apply B/W filter" should produce full original color — no desaturation — regardless
of the "Apply grain" checkbox state.

## Root cause (confirmed by reading code, not yet fixed)

`gui/save_action.py:19`, in `save_kept_jobs`:

```python
job.rendered.convert("L").save(dst, quality=92, optimize=True)
```

This unconditionally converts every saved image to grayscale (`"L"` mode) regardless of
`job.apply_bw`. It predates the `bw-grain-filter` split — before that work, `render_photo`
always produced an `"L"`-mode canvas, so `.convert("L")` here was a harmless no-op. Now that
`render_photo` (`src/pipeline.py`) can produce an `"RGB"`-mode canvas when `apply_bw=False`
(confirmed correct in `tests/test_pipeline.py::test_process_photo_without_bw_produces_rgb_canvas`
and `tests/test_gui_smoke.py::MainWindowWiringTests::test_processing_with_bw_off_produces_color_thumbnail`,
both passing), this line silently clobbers that color output back to grayscale at save time.

So the in-app gallery thumbnail for a B/W-off run is correctly in color (per the passing tests
above); only the saved file on disk is wrong. This also explains why the automated test suite
didn't catch it: no test exercises `save_kept_jobs`/`save_action.py` against a color
(`apply_bw=False`) job — `tests/test_gui_smoke.py::SaveActionTests` only covers jobs built via
`_make_job()`, which is hardcoded to `"L"` mode (`Image.new("L", (600, 600), 128)` in the
test's `job.rendered` setup), so the always-`.convert("L")` bug is invisible to it either way.

**Likely fix shape** (as applied): save in the job's actual rendered mode instead of forcing
`"L"` — `gui/save_action.py` now does `job.rendered.save(dst, ...)`. Covered by a new
`SaveActionTests` case (`test_saves_color_job_as_color_not_grayscale`) asserting a saved
`"RGB"`-mode job isn't grayscale.

## Session update: fixed

Fixed and committed in `5b117d2`. `gui/save_action.py:19` no longer force-converts to `"L"`.

## Comments
