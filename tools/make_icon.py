"""Convert gui/assets/branding/logo.png into build/cropper.ico for the PyInstaller build."""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    out = ROOT / "build" / "cropper.ico"
    out.parent.mkdir(exist_ok=True)
    img = Image.open(ROOT / "gui" / "assets" / "branding" / "logo.png").convert("RGBA")
    side = max(img.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    square.save(out, sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
