# Face detection is producing massive false-positive counts on non-face images

Status: requested 2026-09-21, not scoped, not implemented — note-taking only.

## Context

User's screenshot (Details dialog for `DSCF1631.JPG`, a photo of a shoe display wall on a
pegboard) shows **77 detected "faces"** overlaid as red boxes across shoe silhouettes, pegboard
holes, and shadow patterns - none of them actual faces. This isn't a logged issue yet; no prior
`.scratch/` ticket covers face-detection accuracy specifically (checked: `desktop-tool`,
`post-v1-cleanup`, and `manual-testing-feedback` specs mention faces only in passing, e.g. the
detail-view overlay smoke test, not detection quality).

## Issues

- `issues/01-haar-cascade-false-positives-on-textured-backgrounds.md`
- `issues/02-symmetry-ambiguous-band-may-be-too-wide.md`

## Comments
