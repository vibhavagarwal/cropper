# Show the original (unprocessed) photos as soon as a folder is chosen

Status: requested 2026-09-21, not scoped

## User's request

When browsing to (or typing/dropping) a folder, the photos in that folder should load and
display as-is - before "Process Folder" is clicked - rather than the gallery staying empty
(`_EMPTY_STATE_TEXT` in `gui/review_gallery.py`) until a full run completes.

## Context (not investigated in depth - starting pointers only)

- Today the gallery (`gui.review_gallery.ReviewGallery`) only ever gets populated via
  `add_job`, called from `MainWindow._on_photo_ready` as each `PhotoJob` finishes the full
  pipeline (detection, triage, crop, render) in `ProcessFolderWorker`. There is currently no
  path that shows a raw/original thumbnail before that pipeline runs.
- `InputPanel._on_browse_clicked` / `dropEvent` / the folder-edit text field all just set
  `folder_edit`'s text - none of them currently enumerate or read files in the folder.
- Open questions for whoever scopes this (not decided): is this a *separate* lightweight
  preview strip/grid (raw thumbnails only, no controls), or does it reuse `ReviewGallery`/
  `PhotoCard` in some reduced "not yet processed" state that then gets replaced/upgraded in
  place as each photo finishes processing? The latter is more work but avoids a jarring
  swap-out at the end of a run. Also unclear: should this preview read every file matching
  `pipeline._PHOTO_EXTS` in the folder, same filter `process_folder` already uses?

## Comments
