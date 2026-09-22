# "Load folder" button: preview a folder that's already in the field without re-picking it

Status: implemented 2026-09-21

## Context

Follow-up to `issues/01-preview-original-photos-on-folder-select.md`, which only triggers a
preview on a deliberate Browse/drop action (`InputPanel.folder_selected`), not on every
`folder_edit` text change - intentional, to avoid re-listing a folder on every keystroke.

The gap: on a fresh app launch, `folder_edit` is pre-filled from `AppSettings.last_input_folder`
(the previous session's folder), but since that pre-fill isn't a Browse/drop action, no preview
fires automatically. The user has to re-browse to the *same* folder just to see a preview of
photos that were already sitting there.

## User's request

A third button, "Load folder", alongside Browse and Process Folder:
- **Browse** - unchanged, opens the folder picker.
- **Load folder** (new) - triggers the existing preview behavior for whatever's currently in
  the folder field, regardless of how it got there (typed, pre-filled from last session,
  browsed, dropped).
- **Process Folder** - unchanged, runs the real pipeline.

## Design

`gui/input_panel.py`: new `self.load_button = QPushButton("Load folder")` in `folder_row`,
positioned between Browse and Process Folder. `_on_load_folder_clicked()` re-emits the existing
`folder_selected` signal with `self.folder_edit.text()` (no-op if empty) - reuses
`MainWindow._on_folder_selected`'s existing preview-loading wiring entirely; no new signal or
MainWindow-side code needed.

## Testing

- `InputPanel` tests: clicking Load folder emits `folder_selected` with the field's current
  text; does nothing when the field is empty.
- `MainWindow` end-to-end test: a settings file with `last_input_folder` set, construct the
  window, confirm the gallery is still empty (no auto-preview on launch), click Load folder,
  confirm the preview populates.

## Comments
