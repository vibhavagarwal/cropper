"""Per-photo detail view: what the detection pass found (face boxes, saliency
blob, symmetry score) and, if escalated, the AI's confidence and tier. Not
shown in the main gallery grid by default - opened on demand from a card's
Details button."""
from PIL import ImageDraw

from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout


def render_detection_overlay(job):
    base = job.rendered.convert("RGB").copy()
    draw = ImageDraw.Draw(base)
    if job.detection is not None:
        scale_x = base.width / (job.detection.saliency.heatmap.shape[1] or base.width)
        scale_y = base.height / (job.detection.saliency.heatmap.shape[0] or base.height)
        for face in job.detection.faces:
            x0, y0 = face.x * scale_x, face.y * scale_y
            x1, y1 = (face.x + face.w) * scale_x, (face.y + face.h) * scale_y
            draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=3)
    return base


class DetailViewDialog(QDialog):
    def __init__(self, job, parent=None):
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
        info_label = QLabel("\n".join(info_lines))

        layout = QVBoxLayout(self)
        layout.addWidget(image_label)
        layout.addWidget(info_label)
