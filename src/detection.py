"""Detection pass: face detection (Haar cascade), saliency mapping (spectral
residual), and a symmetry test (mirror-flip comparison). No tilt or perspective
correction - the pipeline brief assumes photos are shot at the intended
orientation and only crops."""
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


_FACE_CASCADE = None


def _face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _FACE_CASCADE = cv2.CascadeClassifier(path)
    return _FACE_CASCADE


def detect_faces(gray: np.ndarray) -> list:
    boxes = _face_cascade().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
    )
    return [FaceBox(int(x), int(y), int(w), int(h)) for (x, y, w, h) in boxes]


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
    faces = detect_faces(gray)
    sal = saliency_map(bgr)
    sym = symmetry_score(gray)
    return DetectionResult(faces=faces, saliency=sal, symmetry_score=sym)
