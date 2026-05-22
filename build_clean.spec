# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

PY_HOME = r"C:\Users\31841\AppData\Local\Programs\Python\Python314"
DLLS_DIR = os.path.join(PY_HOME, "DLLs")
TCL_DIR = os.path.join(PY_HOME, "tcl")

binaries = [
    (os.path.join(DLLS_DIR, "tcl86t.dll"), "."),
    (os.path.join(DLLS_DIR, "tk86t.dll"), "."),
    (os.path.join(DLLS_DIR, "_tkinter.pyd"), "."),
]

datas = [
    (os.path.join(TCL_DIR, "tcl8.6"), os.path.join("tcl", "tcl8.6")),
    (os.path.join(TCL_DIR, "tk8.6"), os.path.join("tcl", "tk8.6")),
    (os.path.join(TCL_DIR, "tcl8"), os.path.join("tcl", "tcl8")),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog',
        '_tkinter',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=['runtime_hook_tkinter.py'],
    excludes=['pkg_resources', 'setuptools', 'pip', 'wheel'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='自动校园网连接',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)
