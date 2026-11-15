"""Persisted app settings (shape, canvas size, filter toggle, last input/output
folders) across restarts, stored as a small local JSON file."""
import json
from dataclasses import asdict, dataclass
from pathlib import Path


LOOKS = ("none", "bw", "moodportrait")


@dataclass
class AppSettings:
    shape: str = "square"
    canvas_long: int = 2400
    apply_bw: bool = True
    # "none" | "bw" | "moodportrait". Empty means an older settings file: derived from apply_bw on load.
    look: str = ""
    apply_grain: bool = True
    grain_size: str = "medium"
    border_size: str = "medium"
    last_input_folder: str = ""
    last_output_folder: str = ""

    def __post_init__(self):
        if self.look not in LOOKS:  # older settings file (or default): derive from apply_bw
            self.look = "bw" if self.apply_bw else "none"

    @classmethod
    def load(cls, path: Path) -> "AppSettings":
        path = Path(path)
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        known = {k: v for k, v in data.items() if k in asdict(cls())}
        return cls(**known)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
