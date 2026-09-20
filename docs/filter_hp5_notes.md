# HP5 filter notes

## Source of the look

Anders Lindborg's "Ilford HP5 Plus 400" recipe for Fujifilm cameras, published by Fuji X Weekly
(URL in `CLAUDE.md`). The author describes the goal as soft highlights and deep but never fully
black shadows, with middle gray as the priority. The recipe is compatible with X-Trans IV and V
cameras, so the X-T5 used for this project can run it in camera.

Recipe settings: Monochrome, DR400, Highlight -1, Shadow +1, NR -4, Sharpness -2, Clarity 0,
Grain Strong Large, WB Daylight +1 Red and -8 Blue, ISO auto up to 6400, exposure
compensation about -2/3 to +2/3.

## Evidence used

Four reference images (799px web copies) are the recipe's own example photos: Astoria and
Columbia River (fog), Stairs in the Forest, Old Fireplace, Two Elk in a Yard. Their luma
statistics are in `reference_stats.json`. No color originals exist, so nothing could be fitted
before and after. Consistent signals across the four:
- Pure grayscale
- Black floor slightly lifted: 0.5th percentile 6 to 9 of 255
- No clipped highlights (99.9th percentile 189 to 229 in the samples)

Not consistent, so treated as scene driven: the white ceiling (186 fog to 226 overcast), the
median (79 to 140) and the tonal spread. DR400 compresses highlights but does not cap them at a
fixed value, so stretching whites to a target would be wrong.

Grain: an earlier measurement suggested grain varied too much to be a filter trait. That was
wrong. The recipe specifies strong, large grain and the reference copies are downscaled about
7.8x, which averages most of it away, so their measured grain reflects scene and resize.

## What the emulation does (src/hp5_emulate.py)

1. White balance gains (red 1.03, green 1.00, blue 0.80) applied before the gray mix. Blue is
   pulled down, so blues render somewhat darker. This is an interpretation, not stated by the source
2. Gray mix, Rec.601 weights renormalised after the gains
3. Tone curve on gamma-encoded luma: `toe_gamma` 1.08, then a soft shoulder (tanh) starting at
   `knee` 0.45 with asymptote `ceiling` 0.80, then a lifted floor of 8/255
4. Slight softening, sigma = 1.5e-4 of the long edge
5. Grain: coarse layer (cell 0.0006 of the long edge, amplitude 0.019) plus a fine 1px layer
   (0.006), stronger in midtones, seeded per filename so reruns are identical

All sizes are fractions of the image long edge, so the look is resolution independent. Run the
filter on the final resized photo, before the border.

## Tuning history

- v1: knee 0.55, ceiling 0.86, grain amp 0.028 and fine 0.009. User feedback: whites were
  popping and some photos came out much brighter, and grain was slightly heavy
- v2 (current): knee 0.45, ceiling 0.80, grain amp 0.019 and fine 0.006. User approved
- Levers not yet pulled: `toe_gamma` 1.15 to 1.2 would darken midtones across the board (bright
  scenes such as pale stone still read light, median 174 on the museum photo)
- Grain calibration used `tools/grain_metric.py`: at 799px wide the metric read about 2.5 to 3.3
  on flat scenes against 0.27 to 3.13 in the references. Foliage reads high regardless

## Results on the nine test photos (X-T5, landscape filter for all)

p0.5 was 10 to 36 (above 18 only when the scene has no real shadows), p99.5 was 182 to 203, and
contrast std was 40 to 57. After the highlight reduction the contrast sits at the low edge of the
reference range (52 to 65), and the garden photo tops out slightly under the reference range.

## Known limits

- Fuji applies DR400 to raw sensor data before tone mapping. On an already processed JPEG the
  emulation can only reshape what the file kept, and clipped highlights cannot be recovered
- The channel mix is a guess. It changes how skies, foliage and water render, so blue sky and
  blue clothing are the best photos to check by eye. Fitting needs a color original paired with
  its finished version
- Four samples from one coastal series is thin. Treat the preset as provisional until it has
  run on a wider set of landscape photos

## Portrait theme, for later

Five sample images (mixed sources, not from the recipe post) look punchier: blacks reach 0,
whites reach 235 to 255, contrast std 63 to 82, and grain varies from almost none to heavy. They
do not look like one fixed function. The user said they will define the portrait treatment
later.
