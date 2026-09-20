"""Interactive, ratio-locked manual crop override. CropBoxState holds the pure
coordinate math (independently testable); CropEditorDialog wraps it with mouse
drag/resize handling and painting."""
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PIL import Image, ImageOps, ImageQt
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPen, QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget

from crop import CropBox


@dataclass
class CropBoxState:
    img_w: int
    img_h: int
    ratio: float
    x: float
    y: float
    w: float

    @property
    def h(self) -> float:
        return self.w / self.ratio

    def move_by(self, dx: float, dy: float) -> None:
        self.x = max(0, min(self.x + dx, self.img_w - self.w))
        self.y = max(0, min(self.y + dy, self.img_h - self.h))

    def resize_to(self, new_w: float) -> None:
        new_w = max(10.0, min(new_w, float(self.img_w)))
        new_h = new_w / self.ratio
        if new_h > self.img_h:
            new_h = float(self.img_h)
            new_w = new_h * self.ratio
        self.w = new_w
        self.x = min(self.x, self.img_w - self.w)
        self.y = min(self.y, self.img_h - self.h)

    def to_crop_box(self) -> CropBox:
        return CropBox(
            x0=self.x / self.img_w, y0=self.y / self.img_h,
            x1=(self.x + self.w) / self.img_w, y1=(self.y + self.h) / self.img_h,
        )


class _CropCanvas(QWidget):
    def __init__(self, pil_image, state: CropBoxState):
        super().__init__()
        self.pixmap = QPixmap.fromImage(ImageQt.ImageQt(pil_image.convert("RGB")))
        self.state = state
        self.setFixedSize(self.pixmap.size())
        self._dragging = False
        self._last_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        pen = QPen(Qt.GlobalColor.red)
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawRect(QRect(int(self.state.x), int(self.state.y),
                                int(self.state.w), int(self.state.h)))

    def mousePressEvent(self, event):
        self._dragging = True
        self._last_pos = event.position()

    def mouseMoveEvent(self, event):
        if self._dragging and self._last_pos is not None:
            delta = event.position() - self._last_pos
            self.state.move_by(delta.x(), delta.y())
            self._last_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def wheelEvent(self, event):
        step = 20 if event.angleDelta().y() > 0 else -20
        self.state.resize_to(self.state.w + step)
        self.update()


class CropEditorDialog(QDialog):
    MAX_DISPLAY_DIM = 1200

    def __init__(self, job, inner_ratio: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Manual crop - {job.filename}")
        source = ImageOps.exif_transpose(Image.open(job.src_path)).convert("RGB")
        scale = min(1.0, self.MAX_DISPLAY_DIM / max(source.width, source.height))
        if scale < 1.0:
            img = source.resize(
                (max(1, round(source.width * scale)), max(1, round(source.height * scale))),
                Image.LANCZOS,
            )
        else:
            img = source
        start_w = min(img.width, round(img.height * inner_ratio))
        self.state = CropBoxState(
            img_w=img.width, img_h=img.height, ratio=inner_ratio,
            x=(img.width - start_w) / 2, y=0, w=start_w,
        )
        self._canvas = _CropCanvas(img, self.state)
        self._accepted = False

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._canvas)
        layout.addWidget(buttons)

    def _on_accept(self):
        self._accepted = True
        self.accept()

    def result_crop_box(self):
        if not self._accepted:
            return None
        return self.state.to_crop_box()
