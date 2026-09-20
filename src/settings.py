"""Persisted app settings (shape, canvas size, filter toggle, last input/output
folders) across restarts, stored as a small local JSON file."""
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppSettings:
    shape: str = "square"
    canvas_long: int = 2400
    apply_filter: bool = True
    last_input_folder: str = ""
    last_output_folder: str = ""

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
