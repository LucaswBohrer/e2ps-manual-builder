# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for the Windows E2PS Manual Builder release."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


# The spec lives in packaging/, while the application entry point is at the repository root.
ROOT = Path(SPECPATH).parent
ASSETS = ROOT / "manual_builder" / "assets"
ICON = ASSETS / "e2ps.ico"

# Qt's PyInstaller hooks collect plugins automatically. PyMuPDF's native library
# is included explicitly because it is responsible for rendering imported PDFs.
datas = [(str(ASSETS), "manual_builder/assets")]
datas += collect_data_files("fitz")
binaries = collect_dynamic_libs("fitz")
hiddenimports = [
    "fitz",
    "fitz.fitz",
    "PIL.ImageQt",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtPrintSupport",
    "PySide6.QtSvg",
]


a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="E2PSManualBuilder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICON),
)

# A one-directory build is intentionally used: it is more reliable for Qt6 and
# PDF native dependencies than a single self-extracting executable.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="E2PS Manual Builder",
)
