# Escalation history dialog: flat chronological list of all past escalations

Status: ready — scoped 2026-09-21

## Context

See `.scratch/escalation-history-view/spec.md` for the full context and decisions — all
resolved, don't re-litigate. The persistence this reads from already exists and needs no
changes: `DecisionLog` (`src/decision_log.py`) already permanently logs every escalation to
`~/.cropper/decision_log.jsonl`.

## Design

- New `gui/escalation_history_dialog.py`, a `QDialog` (pattern similar to `DetailViewDialog` in
  `gui/detail_view_dialog.py`, though simpler — no image, just a list). Takes the app's
  `DecisionLog` instance and displays `decision_log.records`, newest first (reverse
  chronological by `timestamp`), one row per `DecisionRecord`: photo name, formatted
  date/time, tier, provider, cost, confidence.
- Use a `QTableWidget` or similar (not a hand-rolled layout of labels per row) — straightforward
  for a flat tabular list, and gives sensible default column alignment/headers for free.
- `gui/main_window.py`: add a new button to `bottom_row`, e.g. "Escalation history...", styled
  consistently with the existing "Configure API key..." button (both are secondary/"quiet"
  actions per the QSS pass — see `c31db48`). Wire its `clicked` signal to open the new dialog
  with `self.decision_log`, same pattern as `_on_configure_api_key_clicked` opening
  `ApiKeyDialog`.
- No changes needed to `DecisionLog`/`DecisionRecord` — this is a pure read/display feature.

## Explicitly out of scope for this ticket (per the spec's decisions)

- Filtering or sorting beyond the fixed newest-first order.
- Export (CSV or otherwise).
- Any data beyond what `DecisionRecord` already stores.

If a `QTableWidget` is used, note that it can be sorted by clicking column headers "for free" in
Qt without extra code — fine to leave that default behavior in place, but don't build any
additional filter controls or persistence of sort state; that would be scope creep beyond what
was decided.

## Testing

- Dialog construction test: given a `DecisionLog` with several records, the dialog shows the
  expected number of rows, and row order is newest-first.
- Dialog construction test: given an empty `DecisionLog` (no escalations yet), the dialog
  constructs without error and shows zero rows (not a crash) — mirrors how `ReviewGallery`
  already has an empty-state test.
- `MainWindow` wiring test: clicking the new button opens the dialog (same pattern as the
  existing `test_configure_api_key_button_present`-style tests in
  `tests/test_gui_smoke.py::MainWindowWiringTests`).

## Comments
