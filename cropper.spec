# PyInstaller spec for the Cropper Windows build. Run via build.ps1.
# Set CROPPER_CONSOLE=1 to build a console variant for seeing tracebacks.
import os

from PyInstaller.utils.hooks import collect_submodules

console = os.environ.get("CROPPER_CONSOLE") == "1"
name = "Cropper-console" if console else "Cropper"

a = Analysis(
    ["gui/main.py"],
    pathex=["src", "gui"],
    # Modules resolve assets via os.path.dirname(__file__); in a frozen build that is the
    # bundle root, so models/ and assets/ sit directly under it.
    datas=[
        ("src/models", "models"),
        ("src/luts", "luts"),
        ("gui/assets", "assets"),
    ],
    hiddenimports=collect_submodules("keyring.backends") + collect_submodules("providers"),
    excludes=["tkinter", "matplotlib", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
              "PySide6.Qt3DCore", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name=name,
    console=console,
    icon="build/cropper.ico",
)
coll = COLLECT(exe, a.binaries, a.datas, name=name)
