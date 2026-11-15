---
status: accepted
---

# MoodPortrait finds faces with BlazeFace loaded through OpenCV, not YuNet and not mediapipe

The MoodPortrait look (ported from FujiVibe, where it was built as "Rembrandt") puts a pool of light on the face and was
tuned against MediaPipe BlazeFace (short range) boxes and roll. Cropper's YuNet detector is wrong for it: on the four
available photos YuNet gave renders 3.6 to 28.3 mean-absolute-difference away from FujiVibe's, against about 1.8 for
BlazeFace, and it is scale sensitive (on one portrait it found the real face at 1067x1600, only a shirt crest at
2000x3000, and nothing at 24 MP).

**Decision:** `src/face_blaze.py` loads the same 230 KB `blaze_face_short_range.tflite` with `cv2.dnn.readNetFromTFLite`
(OpenCV 4.11, already a dependency) and reimplements MediaPipe's anchors, box decoding and weighted NMS. YuNet is
unchanged and still used for triage and cropping.

**Why not the `mediapipe` package:** measured in a scratch venv, it adds about 100 MB (mediapipe itself 72 MB, plus
matplotlib and others) to a 360 MB frozen build, pulls its own OpenCV pin (5.0) against Cropper's 4.11, and imports in
2.5 s. The OpenCV route detects in 0.02 to 0.17 s and adds only the model file.

**Check:** with its own finder, Cropper's face boxes are within about 0.01 of FujiVibe's (sky 0.308 vs 0.295 width) and
roll within about 3 degrees; renders differ from FujiVibe's by 1.8 to 2.4 mean absolute difference (grain excluded
from ours). Letterbox style (top-left, black, bilinear) was chosen empirically from five variants on four photos.
