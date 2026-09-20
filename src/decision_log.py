"""Per-photo decision log: which photos escalated, which model/tier handled
it, and cost. Visible in-app as a running total and history list (the
pipeline brief's open item #7 - a per-photo decision log for tuning triage
thresholds on real batches)."""
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class DecisionRecord:
    photo_name: str
    escalated: bool
    tier: str
    provider: str
    cost: float
    confidence: float
    timestamp: float


class DecisionLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.records = []
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.records.append(DecisionRecord(**json.loads(line)))

    def add(self, record: DecisionRecord) -> None:
        self.records.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    @property
    def running_cost(self) -> float:
        return sum(r.cost for r in self.records)
