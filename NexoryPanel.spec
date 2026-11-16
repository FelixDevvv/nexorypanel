# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

root = Path(SPECPATH)
icon = (
    str(root / "static" / "icon.ico")
    if sys.platform == "win32"
    else str(root / "static" / "icon.icns")
    if sys.platform == "darwin"
    else None
)

a = Analysis(
    [str(root / "app.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "templates"), "templates"),
        (str(root / "static"), "static"),
    ],
    hiddenimports=["psutil"],
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
    a.datas,
    [],
    name="NexoryPanel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=sys.platform == "win32",
    console=True,
    icon=icon,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="NexoryPanel.app",
        icon=icon,
        bundle_identifier="com.felixdevvv.nexorypanel",
        info_plist={"LSMinimumSystemVersion": "12.0"},
    )
