"""Per-photo detail view: what the detection pass found (face boxes, saliency
blob, symmetry score) and, if escalated, the AI's confidence and tier. Not
shown in the main gallery grid by default - opened on demand from a card's
Details button."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import hp5_emulate as H
from crop import CropBox

from PIL import ImageDraw

from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout


def render_detection_overlay(job):
    base = job.rendered.convert("RGB").copy()
    draw = ImageDraw.Draw(base)
    if job.detection is not None:
        source_h, source_w = job.detection.saliency.heatmap.shape
        crop_box = job.crop_box if job.crop_box is not None else CropBox(0.0, 0.0, 1.0, 1.0)
        crop_w_frac = crop_box.x1 - crop_box.x0
        crop_h_frac = crop_box.y1 - crop_box.y0
        lay = H.layout(job.shape, job.canvas_long)
        border = lay["border"]
        inner_w, inner_h = lay["inner"]
        for face in job.detection.faces:
            fx0, fy0 = face.x / source_w, face.y / source_h
            fx1, fy1 = (face.x + face.w) / source_w, (face.y + face.h) / source_h
            rx0 = min(1.0, max(0.0, (fx0 - crop_box.x0) / crop_w_frac))
            ry0 = min(1.0, max(0.0, (fy0 - crop_box.y0) / crop_h_frac))
            rx1 = min(1.0, max(0.0, (fx1 - crop_box.x0) / crop_w_frac))
            ry1 = min(1.0, max(0.0, (fy1 - crop_box.y0) / crop_h_frac))
            x0, y0 = border + rx0 * inner_w, border + ry0 * inner_h
            x1, y1 = border + rx1 * inner_w, border + ry1 * inner_h
            if x1 > x0 and y1 > y0:
                draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=3)
    return base


class DetailViewDialog(QDialog):
    def __init__(self, job, decision_log=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Details - {job.filename}")
        overlay = render_detection_overlay(job)
        rgb = overlay.tobytes()
        qimage = QImage(rgb, overlay.width, overlay.height,
                         overlay.width * 3, QImage.Format.Format_RGB888)

        image_label = QLabel()
        image_label.setPixmap(QPixmap.fromImage(qimage))

        info_lines = []
        if job.detection is not None:
            info_lines.append(f"Faces detected: {len(job.detection.faces)}")
            info_lines.append(f"Saliency blob fraction: {job.detection.saliency.blob_fraction:.2f}")
            info_lines.append(f"Symmetry score: {job.detection.symmetry_score:.2f}")
        if job.triage_decision is not None:
            info_lines.append(f"Escalation reasons: {', '.join(job.triage_decision.reasons) or 'none'}")
        if job.crop_decision is not None:
            info_lines.append(
                f"AI decision: tier={job.crop_decision.tier}, "
                f"confidence={job.crop_decision.confidence:.2f}"
            )
        if decision_log is not None:
            total_cost = sum(
                r.cost for r in decision_log.records
                if r.photo_name == job.filename and r.escalated
            )
            if total_cost:
                info_lines.append(f"Total cost: ${total_cost:.6f}")
        self.info_label = QLabel("\n".join(info_lines))

        layout = QVBoxLayout(self)
        layout.addWidget(image_label)
        layout.addWidget(self.info_label)
