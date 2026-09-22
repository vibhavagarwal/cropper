# Move "Process Folder" up next to "Browse...", out of its own bottom row

Status: requested 2026-09-21, not scoped

## User's request

Put the "Process Folder" button next to "Browse..." in the folder row, rather than its current
placement in its own row below the "Run settings" box.

## Context (checked, not changed)

`gui/input_panel.py`: today `folder_row` holds `QLabel("Folder:")` / `folder_edit` /
`browse_button`, and `process_button` sits in a separate `process_row` (`addStretch()` then the
button, right-aligned) placed after `settings_group` in the panel's outer `QVBoxLayout`:

```python
folder_row = QHBoxLayout()
folder_row.addWidget(QLabel("Folder:"))
folder_row.addWidget(self.folder_edit)
folder_row.addWidget(self.browse_button)
...
process_row = QHBoxLayout()
process_row.addStretch()
process_row.addWidget(self.process_button)

layout = QVBoxLayout(self)
layout.addLayout(folder_row)
layout.addWidget(self.settings_group)
layout.addLayout(process_row)
```

Straightforward move: add `self.process_button` to `folder_row` (after `browse_button`) and
drop the separate `process_row`. `self.process_button.setProperty("primary", True)` stays
unchanged - it's a placement change, not a style change.

## Not yet decided / worth confirming when scoped

- Whether "Run settings" then sits *below* both folder-picking and the process trigger (i.e. the
  visual order becomes Folder+Browse+Process, then Run settings) reads oddly, since today
  Process Folder comes *after* the settings the user is meant to configure first. Worth flagging
  as a re-think-provoking move, not just a copy-paste of the widget - could also imply
  reordering the Run settings box above the folder row instead, which is a different change.
- The button's current "Stop" toggle text (`.scratch/folder-preview-and-cancel/issues/
  02-stop-button-during-processing.md`, since implemented) has to keep working from its new
  position - no functional change expected, just a placement note for whoever implements this
  to verify.

## Comments
