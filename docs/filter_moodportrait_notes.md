# MoodPortrait filter notes

Ported from FujiVibe ("Rembrandt"). Code: `src/moodportrait.py` (grade + pool of light), `src/face_blaze.py` (faces).
Spec and tickets: `.scratch/moodportrait-filter/`. Pipeline order: LUT, pool of light, then Cropper's own grain.

## Preserved exactly
The shipped `REMBRANDT_PROFILE` values (a test asserts them) and the baked `.cube`. The options FujiVibe tried and
switched off (`forehead_stretch`, `shadow_lift`, moving the brightness cap out) exist as parameters, default off.
Known flaws are kept on purpose: halo around the head, grey forehead patch, dark eyes, dulled bright clothes, only the
largest face used, no-face photos get a frame-centred oval.

## Differences from the FujiVibe renders (measured on four photos, local only)
- **Grain:** not ported. Cropper's grain is HP5-style two-layer grain, not FujiVibe's coarse canvas texture; the
  comparisons below have grain off in Cropper.
- **Crop:** Cropper applies the look to the crop, so the pool and the 20%-of-width minimum pool are relative to the
  crop, not the full frame.
- **Face detector:** Cropper's BlazeFace finder is a reimplementation; boxes within ~0.01-0.02 of FujiVibe's, roll
  within ~3 degrees (4 photos).
- **Pixels:** same face file gives 1.7 to 1.9 mean absolute difference vs FujiVibe's JPEG render (that is the missing
  grain plus JPEG noise); Cropper's own faces 1.8 to 2.4.
- **Input:** JPEG only; EXIF rotation applied by Cropper.

## Speed (numpy, 8 threads, this laptop)
Grade + pool of light: about 1.5 s at 2300x1840, about 8 s at 24 MP. Face detection 0.02 to 0.17 s.
