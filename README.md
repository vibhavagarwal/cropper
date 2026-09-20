# Cropper

Desktop tool that batch-crops photos onto a fixed canvas (square / portrait /
landscape), with an optional HP5-emulation filter, automatic face/saliency
detection to decide the crop, and an explicit escalation path to a paid AI
crop decision (OpenAI) for photos the free pipeline is unsure about.

See [`.scratch/desktop-tool/spec.md`](.scratch/desktop-tool/spec.md) for the
full requirements and [`docs/superpowers/plans/2026-09-20-desktop-tool.md`](docs/superpowers/plans/2026-09-20-desktop-tool.md)
for how it was built.

## Requirements

- Python 3.14 (developed and tested against 3.14.7)
- No other system dependencies — everything else is a pinned `pip` package.

## Setup

Use a virtual environment so this project's pinned dependency versions never
collide with anything else on your machine:

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Running the app

```bash
python gui/main.py
```

Escalating a photo to the paid AI tier requires `OPENAI_API_KEY` to be set in
your environment. Without it, the app runs fully on the free/local pipeline
and shows a status-bar message instead of crashing if you try to escalate.

## Running the tests

```bash
python -m unittest discover -s tests -v
```

On a machine with no display attached, set `QT_QPA_PLATFORM=offscreen` first.

## Project layout

- `src/` — the pipeline: EXIF/layout math, detection, triage, cropping, the
  AI provider interface, cost estimation, decision logging, settings.
- `gui/` — the PySide6 desktop app (`main.py` is the entry point).
- `tests/` — unit tests, mirroring `src/` and `gui/`.
- `tools/` — standalone analysis scripts, not part of the app itself.
