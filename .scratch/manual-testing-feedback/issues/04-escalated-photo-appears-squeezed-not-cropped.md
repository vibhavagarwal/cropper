# Escalated photo appears squeezed/stretched rather than cropped

Status: fixed (commit 5b117d2) — see "Session update" below. The gap itself was confirmed by
code inspection; whether it was *the* actual cause of what the user originally saw was never
proven against a live repro, but the gap is real and is now closed regardless.

## Observed

After escalating one photo (AI-assisted crop), the resulting rendered photo appeared squeezed
(aspect ratio distorted) rather than cleanly cropped to the target shape.

## Diagnosis (code inspection — confirmed this is NOT a bw-grain-filter regression)

Confirmed by reading `src/pipeline.py:render_photo` (current version): the crop/resize geometry
is unchanged by the `bw-grain-filter` work — still `img.crop((x0,y0,x1,y1)).resize((iw, ih),
Image.LANCZOS)`. That ticket only added `apply_bw`/`apply_grain`/`grain_size` parameters and
which `emulate()` call gets made; it never touched cropping. So this is either a pre-existing
gap or unrelated to the filter split — not caused by it.

**Confirmed gap, compared side by side:**

`src/crop.py:formula_crop` (the non-escalated path) computes its box by construction so it is
always exactly on `inner_ratio` — `crop_w`/`crop_h` are derived directly from `inner_ratio`
(`crop.py:27-34`), so `to_pixels()` can never hand `render_photo` an off-ratio box.

`src/pipeline.py:apply_escalation` (`apply_escalation`, lines 83-100) does not have the same
guarantee:

```python
decision = provider.request_crop(buf.getvalue(), metadata, lay["inner_ratio"], tier)
job.crop_decision = decision
x0, y0, x1, y1 = decision.crop_box
job.crop_box = crp.CropBox(x0, y0, x1, y1)
```

It takes `decision.crop_box` straight from the AI provider's response and builds a `CropBox`
with **no check or correction** that its aspect ratio actually matches `lay["inner_ratio"]`
before `render_photo` resizes the cropped region to the fixed `(iw, ih)` inner size. The prompt
in `src/providers/openai_provider.py:48-54` tells the model what ratio to target
(`f"The crop must have width:height ratio {inner_ratio:.4f}."`), but that's a request to the
model, not a code-side guarantee — nothing clamps or corrects the returned box afterward. A
free-form numeric JSON response that's even slightly off-ratio would resize-squeeze exactly as
described.

**This is a real, confirmed gap in the code** (asymmetry between the two crop paths), but
whether it's *the* cause of what the user saw is not proven — that requires either a live
escalation call with a real provider response to inspect, or a unit test asserting
`apply_escalation` rejects/corrects an off-ratio `decision.crop_box`.

## Likely fix shape (as applied)

Clamped/adjusted the returned box to the correct ratio before building `CropBox`: a new
`_correct_crop_ratio` helper in `src/pipeline.py` adjusts an off-ratio `decision.crop_box` to
match `lay["inner_ratio"]` (keeping its center fixed) before `apply_escalation` renders it.
Covered by `test_apply_escalation_corrects_off_ratio_crop_box_from_provider`, which feeds a
fake provider a deliberately off-ratio box and asserts the correction happens.

## Session update: fixed

Fixed and committed in `5b117d2`.

## Notes for whoever picks this up

- Worth checking whether this happens on every escalated photo or only some, and whether it
  correlates with a specific provider/tier response — that would help decide between "always
  validate" vs. "the model is usually fine, just guard the edge case."

## Comments
