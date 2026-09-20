"""Triage gate: decide per photo whether to escalate to paid AI reasoning or
handle it with the formula crop. THRESHOLDS are initial guesses - like PARAMS
in hp5_emulate.py, tune them against labeled real batches, not eyeballed."""
from dataclasses import dataclass

THRESHOLDS = dict(
    saliency_blob_max=0.85,
    symmetry_ambiguous_low=0.55,
    symmetry_ambiguous_high=0.80,
)


@dataclass(frozen=True)
class TriageDecision:
    escalate: bool
    reasons: list


def triage(detection, image_area: int, thresholds: dict = THRESHOLDS) -> TriageDecision:
    reasons = []
    if detection.saliency.blob_fraction >= thresholds["saliency_blob_max"]:
        reasons.append("saliency spans nearly the whole frame")
    if len(detection.faces) >= 2:
        areas = sorted((f.area for f in detection.faces), reverse=True)
        if areas[0] < 1.5 * areas[1]:
            reasons.append("multiple faces with no clear primary subject")
    if detection.saliency.touches_edge:
        reasons.append("saliency blob touches an edge or corner")
    if thresholds["symmetry_ambiguous_low"] <= detection.symmetry_score <= thresholds["symmetry_ambiguous_high"]:
        reasons.append("symmetry score is ambiguous")
    return TriageDecision(escalate=bool(reasons), reasons=reasons)
