# Face source: BlazeFace detector giving a MoodPortrait `Face`

Status: resolved
Spec: ../spec.md

## What to build

A face finder for the filter only, using MediaPipe's BlazeFace short-range model, the detector the look was tuned on.
It takes the EXIF-corrected original and the crop box and returns a `Face` in **crop** coordinates (fractions) with a
roll, or `None` when there is no face. YuNet stays as it is for triage and cropping; nothing there changes.

## Why not YuNet (prototype finding, 2026-11-11)

A scratchpad prototype (not in the repo) rendered four FujiVibe photos. With BlazeFace faces the output matched the
FujiVibe renders to about 1.8/255 mean absolute difference (grain not included). With YuNet faces it was worse: mean
difference 3.6 to 8.7 on three photos, and on `DSCF1170` (hat portrait) 28.3. YuNet is scale-sensitive: at 1067x1600
it found the real face (score 0.89), at 2000x3000 only a false positive on the shirt crest (0.62), and at the full
5152x7728 nothing. `pipeline.process_photo` runs YuNet on the full-resolution image, so existing triage may also miss
faces on big photos (out of scope here; worth its own note).

## Steps

1. **Measure first.** In a scratch venv (not the project's), install `mediapipe` and record: wheel/install size,
   frozen PyInstaller build size delta against the current 360 MB, import and first-detect time, and whether it runs
   on Python 3.14 here (FujiVibe's venv used mediapipe 1.2.2 on 3.14). Write the numbers in Comments.
2. **Choose the implementation from the numbers.**
   a. MediaPipe `FaceDetector` (preferred): `min_detection_confidence` 0.4, largest face by box area, as
      `make_faces.py`.
   b. If it is too heavy: load the same `.tflite` with OpenCV (`cv2.dnn.readNetFromTFLite`, OpenCV 4.11) and port
      BlazeFace anchor generation, box decoding and NMS. First confirm OpenCV supports every op in the model; if it
      does not, stop and report.
   Record the choice in an ADR in `docs/adr/`.
3. Copy `app/src/main/assets/blaze_face_short_range.tflite` from FujiVibe (229,746 bytes) to `src/models/`; bundle it
   in `cropper.spec` `datas` next to the YuNet model. Add a third-party notice (model and MediaPipe are Apache 2.0).
4. Port the box and roll rules from `.scratch/rembrandt/tools/make_faces.py`: box = eyebrows to chin as the detector
   returns it; centre and size as fractions of the image; roll = `atan2(dy*H, dx*W)` between the two eye keypoints
   sorted left to right, positive clockwise on screen.
5. Detect on a copy downscaled to about 1600 px on the long edge (fractions carry over to any size). Check on large
   originals that BlazeFace does not fail the way YuNet did.
6. Remap original-image fractions into the crop: `(c - x0)/(x1 - x0)` for centre, `w/(x1 - x0)` for size, same in y.
7. Store the `Face` (or none) on `PhotoJob` so re-renders (manual crop, escalation) do not re-detect.
8. If detection raises, treat it as "no face" (oval fallback) and do not fail the photo, as FujiVibe does.

## Acceptance

- [ ] Measurement numbers and the implementation choice recorded, with an ADR
- [ ] On the FujiVibe photos, Cropper's face matches the `.face.txt` files (same centre, size and roll within a
      small tolerance); compared locally against the files on disk, nothing personal committed
- [ ] Roll sign and units verified on a tilted face (positive = clockwise on screen)
- [ ] Remap verified with a crop that excludes part of the face
- [ ] Works on a 24 MP original (does not miss the face)
- [ ] Existing detection and triage tests still pass unchanged

## Comments

Chose OpenCV-loaded BlazeFace (option b), no mediapipe: measured mediapipe at ~100 MB extra (361 MB venv, mediapipe 72 MB, matplotlib, OpenCV 5.0 pin), 2.5 s import. See `docs/adr/0001-blazeface-via-opencv-for-moodportrait.md`. `src/face_blaze.py`: boxes within ~0.01-0.02 of FujiVibe's face files, roll within ~3 degrees; works at 24 MP (0.05-0.17 s, detects on a 1600 px copy). Not done: storing the face on `PhotoJob` (belongs to ticket 05, integration). Roll sign was checked only by agreement with the reference files on 4 photos.
