# Canvas-texture grain

Status: dropped (decision 2026-11-11)
Spec: ../spec.md

Not building a port of FujiVibe's canvas grain. Cropper already has user-controllable grain (apply checkbox and size),
and the user chose to use that. No work here.

## Follow-up for ticket 05

Make sure Cropper's existing grain can be applied on top of the MoodPortrait output (the current RGB grain path in
`hp5_emulate.emulate` with `apply_bw=False` does this on a colour image), and report in the notes that the grain
look differs from FujiVibe's canvas tooth.
