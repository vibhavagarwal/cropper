# Build a Windows exe with PyInstaller

Status: resolved
Spec: ../spec.md

## What to build

Add a checked-in PyInstaller spec (`cropper.spec`) and a build script that produce a windowed,
one-folder Windows build of `gui/main.py`, per `../spec.md`.

## Steps

1. Check PyInstaller support for Python 3.14 and the pinned dependencies; if unsupported, stop
   and record the decision (ADR in `docs/adr/`) before continuing.
2. Add `pyinstaller` as a dev/build dependency (keep it out of the runtime `requirements.txt`,
   e.g. `requirements-build.txt`).
3. Write `cropper.spec`: `pathex` for `src` and `gui`, `datas` for the YuNet model and
   `gui/assets/`, `hiddenimports` for `keyring.backends.Windows` as needed, windowed mode,
   icon from `logo.png` (converted to `.ico`).
4. Add a build script (e.g. `build.ps1`) that runs PyInstaller from the venv.
5. Build, then smoke-test the output per the acceptance criteria below, ideally on a machine
   without Python.
6. Update README Setup/Limitations; add `build/` and `dist/` to `.gitignore` if not present.

## Acceptance criteria

- [ ] `build.ps1` produces `dist/Cropper/Cropper.exe` from a clean checkout
- [ ] Launches by double-click with no Python installed; no console window
- [ ] Face detection works, logo and icons render, dark theme applied
- [ ] Process Folder on a sample folder gives the same results as from source
- [ ] API key save/load works via Credential Manager in the frozen build; no-key escalation
      shows the status-bar message instead of crashing
- [ ] README updated; ADR added if tool/Python version decision deviates from the spec

## Comments

Resolved. PyInstaller 6.22.3 lists Python 3.14 support, so no ADR (no deviation from the spec).
Files: `cropper.spec`, `build.ps1`, `requirements-build.txt`, `tools/make_icon.py`. No app code changed:
frozen modules' `__file__` is the bundle root, so `datas` go to `models/` and `assets/`.

Verified: `build.ps1` builds `dist/Cropper/Cropper.exe` (360 MB folder), launches windowed, window opens.
A probe frozen with the same model/hiddenimports settings gave byte-identical detection, `process_folder`
render hashes, and keyring save/load/clear versus running from source.

Not verified (needs a human): launch on a machine without Python; visual check of logo, icons and dark
theme in the exe; the no-key status-bar message in the frozen GUI.
