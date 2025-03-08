# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

# If you have a folder with images (e.g. "detect-img") that you want to include:
datas = []
if os.path.isdir("detect-img"):
    # Include all files in detect-img into a folder "detect-img" in the exe bundle
    datas.append(("detect-img", "detect-img"))

a = Analysis(
    ['src/yasumi.py'],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Yasumi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False if you want a windowed app (no console)
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Yasumi'
)
