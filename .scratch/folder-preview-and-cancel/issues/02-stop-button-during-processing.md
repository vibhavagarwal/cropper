# Add a Stop/Cancel button during "Process Folder", so a bad run can be aborted and re-run

Status: requested 2026-09-21, not scoped

## User's request

If a mistake was made in the run settings (shape, canvas size, B/W, grain, border, etc.) before
clicking "Process Folder," there's currently no way to stop the run in progress - it has to run
to completion before the settings can be corrected and re-run.

## Context (not investigated in depth - starting pointers only)

- Processing runs on `gui/workers.py`'s `ProcessFolderWorker` (a `QThread`), which iterates
  `pipeline.process_folder` (a generator) and emits `photo_ready` per photo, `finished_all` at
  the end. `MainWindow._start_processing` disables re-entry while a worker `isRunning()` but has
  no cancel path.
- `QThread` has no built-in graceful-stop primitive here; the natural shape is likely a
  cooperative flag `ProcessFolderWorker` checks between photos (e.g. an `is_cancelled()` check
  inside its `run()` loop, or breaking out of the `process_folder` generator early) rather than
  `terminate()` (unsafe - can kill mid-write/mid-I/O). `pipeline.process_folder`/`process_photo`
  don't currently accept any cancellation signal.
- Open questions for whoever scopes this (not decided): should a stop leave already-processed
  photos in the gallery (partial results kept), or discard them along with the run? Should
  "Process Folder" become a toggle (same button, changes to "Stop") or a separate button that's
  only enabled while a worker is running (mirrors how `escalate_selected_button` etc. are
  enabled/disabled elsewhere in `gui/main_window.py`)? Does stopping need to also cancel an
  in-flight `EscalationWorker`, or is this scoped to `ProcessFolderWorker` only (the user's
  wording was specifically about mis-selected run settings, i.e. the formula-crop pass, not
  escalation)?

## Comments
