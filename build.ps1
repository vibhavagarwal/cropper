# Build dist/Cropper/Cropper.exe (one-folder, windowed). Pass -Console for a console variant.
param([switch]$Console)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = ".venv\Scripts\python.exe"
& $py -m pip install -q -r requirements-build.txt
& $py tools\make_icon.py
$env:CROPPER_CONSOLE = if ($Console) { "1" } else { "0" }
& $py -m PyInstaller cropper.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
