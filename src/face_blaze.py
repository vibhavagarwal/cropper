"""BlazeFace (short range) face finder for the MoodPortrait filter.

The look was tuned against MediaPipe's BlazeFace boxes, so the filter uses the same model. The 230 KB .tflite is
loaded straight through OpenCV's dnn module (no mediapipe dependency, which would add ~100 MB and an OpenCV pin),
and the anchor generation, box decoding and weighted NMS from MediaPipe's face_detection_short_range graph are
reimplemented here. YuNet (src/detection.py) is untouched and still used for triage and cropping.

Model: blaze_face_short_range.tflite, Apache License 2.0, Google (MediaPipe).
Output is each face (largest first; the filter lights up to two large ones) as fractions of the image (centre, size) plus the head roll in radians, positive
clockwise on screen, taken from the eye keypoints, matching FujiVibe's tools/make_faces.py.
"""
import math
import os
from dataclasses import dataclass

import cv2
import numpy as np

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "blaze_face_short_range.tflite")
_INPUT = 128
_SCORE_THRESHOLD = 0.4          # FujiVibe's min_detection_confidence
_NMS_IOU = 0.3                  # MediaPipe's min_suppression_threshold
_DETECT_MAX_EDGE = 1600         # detect on a copy this size; results are fractions, so they apply at any size

_NET = None
_ANCHORS = None


@dataclass(frozen=True)
class BlazeFace:
    """Fractions of the image. roll in radians, positive clockwise on screen."""
    cx: float
    cy: float
    w: float
    h: float
    roll: float
    score: float


def _net():
    global _NET
    if _NET is None:
        _NET = cv2.dnn.readNetFromTFLite(_MODEL_PATH)
    return _NET


def _anchors() -> np.ndarray:
    """896 anchor centres (x, y) in 0..1: 16x16 cells x2, then 8x8 cells x6 (fixed 1x1 anchor size)."""
    global _ANCHORS
    if _ANCHORS is None:
        pts = []
        for fm, per_cell in ((16, 2), (8, 6)):
            for y in range(fm):
                for x in range(fm):
                    pts.extend([((x + 0.5) / fm, (y + 0.5) / fm)] * per_cell)
        _ANCHORS = np.asarray(pts, np.float32)
    return _ANCHORS


def _letterbox(rgb: np.ndarray):
    """Fit the image into 128x128 keeping its aspect ratio, anchored top-left, padded with black. Bilinear resize.
    These choices were picked empirically: of five padding/interpolation/anchor variants tried, this one reproduced
    the reference (MediaPipe 1.2.2) boxes and roll best on the four available photos.
    Returns the tensor image and (scale_x, scale_y, pad_x, pad_y) in fractions of the 128 square."""
    h, w = rgb.shape[:2]
    s = _INPUT / max(h, w)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    small = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((_INPUT, _INPUT, 3), np.uint8)
    canvas[:nh, :nw] = small
    return canvas, (nw / _INPUT, nh / _INPUT, 0.0, 0.0)


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def find_faces(rgb: np.ndarray) -> list:
    """All BlazeFace faces in an RGB uint8 image (already EXIF-upright), largest first. Any failure is 'no faces'."""
    try:
        return _find_faces(rgb)
    except Exception:  # noqa: BLE001 - a detector problem must never fail a photo; the look falls back to its oval
        return []


def find_face(rgb: np.ndarray):
    """The largest face, or None."""
    faces = find_faces(rgb)
    return faces[0] if faces else None


def _find_faces(rgb: np.ndarray) -> list:
    h, w = rgb.shape[:2]
    if max(h, w) > _DETECT_MAX_EDGE:
        s = _DETECT_MAX_EDGE / max(h, w)
        rgb = cv2.resize(rgb, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
        h, w = rgb.shape[:2]
    tensor_img, (sx, sy, padx, pady) = _letterbox(rgb)
    blob = ((tensor_img.astype(np.float32) - 127.5) / 127.5).transpose(2, 0, 1)[None]
    net = _net()
    net.setInput(blob)
    out = dict(zip(net.getUnconnectedOutLayersNames(), net.forward(net.getUnconnectedOutLayersNames())))
    scores = 1.0 / (1.0 + np.exp(-np.clip(out["classificators"].reshape(-1), -60, 60)))
    raw = out["regressors"].reshape(-1, 16)
    anchors = _anchors()

    keep = np.flatnonzero(scores >= _SCORE_THRESHOLD)
    if keep.size == 0:
        return []
    dets = []
    for i in keep[np.argsort(-scores[keep])]:
        r, a = raw[i], anchors[i]
        xc, yc = r[0] / _INPUT + a[0], r[1] / _INPUT + a[1]
        bw, bh = r[2] / _INPUT, r[3] / _INPUT
        kp = [(r[4 + 2 * k] / _INPUT + a[0], r[5 + 2 * k] / _INPUT + a[1]) for k in range(6)]
        dets.append({"box": (xc - bw / 2, yc - bh / 2, xc + bw / 2, yc + bh / 2), "kp": kp, "score": float(scores[i])})

    # Weighted NMS as MediaPipe: each cluster is the score-weighted mean of the boxes/keypoints overlapping its best.
    clusters, remaining = [], dets
    while remaining:
        best = remaining[0]
        group = [d for d in remaining if _iou(best["box"], d["box"]) > _NMS_IOU]
        remaining = [d for d in remaining if _iou(best["box"], d["box"]) <= _NMS_IOU]
        wsum = sum(d["score"] for d in group)
        box = tuple(sum(d["box"][j] * d["score"] for d in group) / wsum for j in range(4))
        kp = [tuple(sum(d["kp"][k][j] * d["score"] for d in group) / wsum for j in range(2)) for k in range(6)]
        clusters.append({"box": box, "kp": kp, "score": best["score"]})

    def to_image(x, y):  # undo the letterbox: 128-square fractions -> fractions of the (resized) image
        return (x - padx) / sx, (y - pady) / sy

    def area(c):
        x0, y0 = to_image(c["box"][0], c["box"][1])
        x1, y1 = to_image(c["box"][2], c["box"][3])
        return (x1 - x0) * (y1 - y0)

    faces = []
    for c in sorted(clusters, key=area, reverse=True):
        x0, y0 = to_image(c["box"][0], c["box"][1])
        x1, y1 = to_image(c["box"][2], c["box"][3])
        eyes = sorted((to_image(*c["kp"][0]), to_image(*c["kp"][1])))  # image-left eye first
        roll = math.atan2((eyes[1][1] - eyes[0][1]) * h, (eyes[1][0] - eyes[0][0]) * w)
        faces.append(BlazeFace(float((x0 + x1) / 2), float((y0 + y1) / 2), float(x1 - x0), float(y1 - y0),
                               float(roll), c["score"]))
    return faces
