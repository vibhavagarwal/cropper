# Default output folder isn't shown to the user, and save confirmation is easy to miss

Status: reported

## Observed

User asked: what is the default save/output folder if they never chose one via "Choose output
folder"? Nothing in the UI currently answers that question before they click Save.

## What the code currently does (for reference, not a fix)

`MainWindow.output_folder()` (`gui/main_window.py:108`) returns the input folder path with
`/out` appended when no override has been set via the output-folder picker. This default is
never displayed anywhere in the input panel or gallery header — the user only finds out by
reading the status bar message after clicking Save, or by inspecting the filesystem.

`_on_save_clicked` (`gui/main_window.py:263`) does already show a status bar message with the
count and destination folder after saving (`f"Saved {len(written)} photo(s) to {out_folder}."`),
but it's a transient status-bar message (auto-clears after 5s), not a prompt/modal — easy to
miss, same category of complaint the batch-escalation summary had before it was given a modal
in the last UI pass (see `.scratch/post-v1-cleanup/issues/01-ui-ux-cleanup.md`).

## Requirement (user's own wording, verbatim ask — not to be diluted into a generic "UX polish" item)

> What is the default folder to save if I didn't choose the output folder? Either it should say
> this is the default and then when save is completed, it should prompt with number of files
> saved and where?

Two concrete, separate requirements, both required:

1. **Before Save**: the UI must show the output folder that will be used, explicitly labeled as
   the default, whenever the user hasn't chosen one via "Choose output folder..." — not left for
   the user to infer or discover only after saving.
2. **After Save**: a prompt (not a transient status-bar message that disappears after 5s) that
   states the number of files saved and the destination folder — a durable, visible
   confirmation, on the same footing as the modal batch-escalation summary already gets
   (`.scratch/post-v1-cleanup/issues/01-ui-ux-cleanup.md`), not weaker than it.

Both parts are required — showing the default alone without the post-save prompt, or vice
versa, does not satisfy this ticket.

## Session update: both parts implemented

1. **Default folder shown before Save**: `MainWindow` now has an `output_folder_label` (added in
   `gui/main_window.py`, placed under the input panel) that always shows the folder Save will
   use, updated live as the input folder changes or an override is chosen via "Choose output
   folder...". It reads `"Output folder (default): <path>"` when no override is set, and
   `"Output folder: <path>"` (no "default" wording) once the user has picked one explicitly.
2. **Durable post-save prompt**: `_on_save_clicked` now shows a `QMessageBox.information` (or
   `.warning` if any files failed to save) stating the count saved and destination folder, in
   addition to the existing status bar message — on the same footing as the batch-escalation
   summary modal, not just the transient 5s status bar text.

New tests (TDD, written failing before the fix): `test_output_folder_label_shows_default_before_save`,
`test_output_folder_label_reflects_chosen_override`, and
`test_save_shows_durable_confirmation_with_count_and_folder` in
`tests/test_gui_smoke.py::MainWindowWiringTests`. Three pre-existing tests that called
`window._on_save_clicked()` directly (`test_save_writes_only_kept_jobs`,
`test_save_removes_saved_jobs_but_keeps_unselected_ones_visible`,
`test_save_button_disabled_after_saving_all_kept`) had to be updated to mock
`QMessageBox.information`, since the new modal would otherwise block the test's event loop
waiting for a user click that never comes. All 35 tests in `MainWindowWiringTests` pass.

## Comments
