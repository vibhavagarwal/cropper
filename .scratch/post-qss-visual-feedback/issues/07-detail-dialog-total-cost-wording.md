# Detail dialog: rename "Total cost" to "Estimated cost for escalation"

Status: requested 2026-09-21, not scoped

## User's request

In the Details dialog (`gui/detail_view_dialog.py:74`), the `"Total cost: $..."` line should
be reworded to `"Estimated cost for escalation"`, since that's what the figure actually is -
the summed cost of escalation calls for this photo, not a total of anything else.

## Context (checked, not changed)

```python
# gui/detail_view_dialog.py:68-74
if decision_log is not None:
    total_cost = sum(
        r.cost for r in decision_log.records
        if r.photo_name == job.filename and r.escalated
    )
    if total_cost:
        info_lines.append(f"Total cost: ${total_cost:.6f}")
```

Single-line text change - the underlying computation (sum of `DecisionLog` records for this
photo where `escalated`) already matches the requested wording, nothing else needs to change.
Existing test `tests/test_gui_smoke.py::DetailViewDialogTests::test_shows_total_cost_from_decision_log_for_this_photo`
currently asserts on `"0.0501"` appearing in `info_label.text()` (the number, not the literal
label text) - worth double-checking whether it also asserts the literal `"Total cost"` string
before assuming no test updates are needed.

## Comments
