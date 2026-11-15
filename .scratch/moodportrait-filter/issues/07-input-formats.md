# Accept more input formats (only if D3 says so)

Status: dropped (D3 decided 2026-11-11: JPEG only)
Spec: ../spec.md

## Context

`pipeline._PHOTO_EXTS = {".jpg", ".jpeg"}`. EXIF rotation is already applied in every load path
(`ImageOps.exif_transpose`), so FujiVibe's "pre-rotate your photos" limitation does not carry over. PNG is a one-line
addition (no new dependency). HEIC needs `pillow-heif` (adds a native wheel to the PyInstaller build). RAW needs
`rawpy` plus a decision on demosaic, white balance and colour space (the look assumes sRGB input).

## Steps

1. Wait for D3. Add only what was asked for, to `list_photo_paths` and the preview path, behind a test with a tiny
   synthetic file per format.
2. Update `cropper.spec` hidden imports/datas and the README format list.

## Acceptance

- [ ] Each accepted format loads upright and colour-correct (sRGB) through `process_photo` and `load_preview`
- [ ] Output of existing JPEG inputs unchanged

## Comments

User decision: JPEG only; Cropper does not use RAW or other formats. No work here. EXIF rotation is already applied.
