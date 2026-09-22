"""Detection pass: face detection (YuNet, a small DNN face detector), saliency
mapping (spectral residual), and a symmetry test (mirror-flip comparison). No
tilt or perspective correction - the pipeline brief assumes photos are shot at
the intended orientation and only crops."""
import os
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def area(self) -> int:
        return self.w * self.h


@dataclass(frozen=True)
class SaliencyResult:
    heatmap: np.ndarray
    blob_fraction: float
    touches_edge: bool


@dataclass(frozen=True)
class DetectionResult:
    faces: list
    saliency: SaliencyResult
    symmetry_score: float


# Was a Haar cascade (haarcascade_frontalface_default.xml) - swapped for this
# DNN detector because the cascade false-positived heavily on repetitive,
# textured non-face backgrounds (pegboard holes, fabric weave), which fed
# directly into triage's "multiple faces" condition.
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "face_detection_yunet_2023mar.onnx")
_FACE_DETECTOR = None


def _face_detector():
    global _FACE_DETECTOR
    if _FACE_DETECTOR is None:
        _FACE_DETECTOR = cv2.FaceDetectorYN.create(
            _MODEL_PATH, "", (320, 320), score_threshold=0.6
        )
    return _FACE_DETECTOR


def detect_faces(bgr: np.ndarray) -> list:
    detector = _face_detector()
    h, w = bgr.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(bgr)
    if faces is None:
        return []
    boxes = []
    for f in faces:
        x, y, fw, fh = f[:4]
        x, y = max(0, int(round(x))), max(0, int(round(y)))
        boxes.append(FaceBox(x, y, int(round(fw)), int(round(fh))))
    return boxes


def saliency_map(bgr: np.ndarray, blob_threshold: float = 0.5) -> SaliencyResult:
    saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
    success, heatmap = saliency.computeSaliency(bgr)
    if not success:
        raise RuntimeError("saliency computation failed")
    heatmap = heatmap.astype(np.float32)
    mask = heatmap >= blob_threshold
    blob_fraction = float(mask.mean())
    h, w = mask.shape
    edge_band = max(1, round(0.03 * max(h, w)))
    touches_edge = bool(
        mask[:edge_band, :].any() or mask[-edge_band:, :].any()
        or mask[:, :edge_band].any() or mask[:, -edge_band:].any()
    )
    return SaliencyResult(heatmap=heatmap, blob_fraction=blob_fraction, touches_edge=touches_edge)


def symmetry_score(gray: np.ndarray) -> float:
    flipped = np.fliplr(gray)
    diff = np.abs(gray.astype(np.float32) - flipped.astype(np.float32))
    return float(1.0 - diff.mean() / 255.0)


def detect(bgr: np.ndarray) -> DetectionResult:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    faces = detect_faces(bgr)
    sal = saliency_map(bgr)
    sym = symmetry_score(gray)
    return DetectionResult(faces=faces, saliency=sal, symmetry_score=sym)
