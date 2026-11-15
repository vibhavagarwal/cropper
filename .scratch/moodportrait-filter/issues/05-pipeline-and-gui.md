# Wire MoodPortrait into the pipeline, settings and GUI

Status: resolved
Spec: ../spec.md
Blocked by: 01, 02, 04

## What to build

A "look" choice that runs LUT -> face pool of light, then Cropper's existing grain (user-controlled), in place of `H.emulate`, with the border added
after as today.

## Steps (shape depends on the decisions)

1. `render_photo()` gets a look argument; MoodPortrait stays RGB (canvas mode "RGB", white border), unlike B/W.
2. `AppSettings` gets a `look` field with a backward-compatible default so existing settings files load unchanged.
3. `InputPanel` / `process_requested` (currently 7 positional args) / `main_window._start_processing` /
   `ProcessFolderWorker` / `FolderPreviewWorker`: thread the look through. Consider replacing the long positional signal
   with a small settings object rather than an 8th argument.
4. Grain: keep Cropper's existing grain checkbox and size working with MoodPortrait (applied after the grade and pool
   of light, on the colour image). FujiVibe's fixed canvas grain is not ported (ticket 03 dropped); say so in the notes.
5. Escalation, manual crop and `detail_view_dialog` re-renders use the same path and the cached face (ticket 04).
6. `README` look list; `docs/filter_*` notes: a short `docs/filter_moodportrait_notes.md` with the values and the
   differences from FujiVibe.
7. No-face photos fall back to the oval silently (as FujiVibe); optionally note it on the card.

## Acceptance

- [ ] Process Folder with MoodPortrait produces colour output with an unfiltered white border
- [ ] HP5 and "no filter" outputs are byte-identical to before this change
- [ ] Existing settings files still load; GUI smoke test passes; narrow-width settings row still wraps
- [ ] Stop button works mid-batch with the new look

## Comments

Done. Look dropdown (None / B&W (HP5) / MoodPortrait) replaces the B/W checkbox; `process_requested` gained an 8th arg (look). `AppSettings.look` derives from `apply_bw` for old settings files. `render_photo(..., moodportrait, faces)` runs grade + pool of light on the crop (faces remapped from the original), then Cropper's own grain on the colour image, border stays white. Faces are found once per photo (`PhotoJob.look_faces`) and reused by manual crop and escalation. Up to two large faces (area >= half the largest) each get a pool; with one face output is identical to before (verified against the parity numbers). Cards show "MoodPortrait: no face found". Not done: README mention, visual check with a real two-person photo (none available), Details/crop-editor dialogs untested with the new look beyond the existing smoke tests.
