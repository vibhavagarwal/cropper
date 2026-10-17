# Windows exe packaging

Status: spec only, not started. Implement in a fresh session (see CLAUDE.md session scope).

## Context

The README's "Limitations" section lists "Local-only, run-from-source. No installer or packaged
build." Today the app needs Python 3.14, a venv and `pip install -r requirements.txt`, then
`python gui/main.py`. The goal is a double-clickable Windows build so the app can be run (and
shown off) without a Python toolchain.

## Goal

A reproducible build command that produces a Windows build of Cropper that launches by
double-click on a machine with no Python installed, and behaves identically to
`python gui/main.py`.

## Proposed approach

PyInstaller, driven by a checked-in `.spec` file and a one-line build script.

## Things the implementation must handle (found by reading the code)

1. **Bundled data files**: the YuNet model `src/models/face_detection_yunet_2023mar.onnx`
   (`src/detection.py:42`, path via `os.path.dirname(__file__)`), `gui/assets/icons/` and
   `gui/assets/branding/logo.png` (`gui/main.py:11-12`, `gui/main_window.py:41`). All are
   resolved relative to `__file__`, which works in a frozen build only if the files are added
   as PyInstaller `datas` at matching relative locations (or the paths are made `sys._MEIPASS`
   aware).
2. **`sys.path.insert` hacks**: `gui/*.py` insert `../src` and `gui/` into `sys.path`
   (`gui/main_window.py:12-13`, `gui/workers.py:6`, etc.), and modules import each other as
   top-level names (`from detection import ...`). PyInstaller's import analysis may miss these;
   expect to need `pathex=["src", "gui"]` in the spec, or `hiddenimports`.
3. **Python 3.14 compatibility**: verify the PyInstaller release supports 3.14 and that the
   pinned wheels (PySide6 6.11.2, opencv-contrib-python 4.11.0.86, numpy 2.5.3, scipy 1.18.1)
   freeze cleanly. If PyInstaller can't handle 3.14, decide between building on a lower Python
   or another tool (e.g. Nuitka) - record the decision as an ADR in `docs/adr/`.
4. **`keyring`**: the API key is stored via the Windows Credential Manager backend
   (`src/api_key_store.py`). Backends are discovered via entry points, which PyInstaller does
   not collect by default - likely needs `hiddenimports` for `keyring.backends.Windows` (and
   possibly `collect_submodules`/metadata for `keyring`). Must verify save/load of a key works
   in the frozen build.
5. **User data location**: settings and decision log already live in `~/.cropper/`
   (`gui/main_window.py:53,56`), independent of install dir - no change needed, just confirm.
6. **Console window**: build as windowed (no console), with a way to see tracebacks when
   debugging (e.g. a `--console` variant or log file).
7. **Size / startup**: scipy + opencv-contrib + PySide6 are large. Compare one-folder vs
   one-file; one-file self-extracts on each launch (slow start, more antivirus false positives).
   Default recommendation: one-folder build, zipped for distribution. Consider trimming
   unused Qt modules and scipy submodules via `excludes`.
8. **Icon**: app/exe icon from the existing logo (convert `logo.png` to `.ico`).

## Out of scope

- A proper installer (MSI/Inno Setup/MSIX), code signing, auto-update.
- macOS/Linux builds.
- CI/release automation (separate item; the README also lists this as missing).
- Any behaviour changes to the app itself.

## Acceptance criteria

- One documented command builds the exe from a clean checkout.
- Built app launches by double-click on a machine/VM without Python.
- Face detection works (model loaded), icons and logo render, dark theme applied.
- Process Folder runs on a sample folder and produces the same results as from source.
- Saving an API key and reopening the app retrieves it from Credential Manager; with no key,
  escalation shows the existing status-bar message rather than crashing.
- README "Limitations" and "Setup" sections updated to describe the build; ADR added if a
  non-PyInstaller tool or Python version is chosen.
