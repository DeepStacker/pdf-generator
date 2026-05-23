# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# We collect dynamic library files for NumPy safely.
numpy_dlls = collect_dynamic_libs('numpy')

# Pack certifi certificates and local font assets
datas = [('fonts', 'fonts')] + collect_data_files('certifi')

# Collect numpy.random submodules
np_extra = [m for m in collect_submodules('numpy.random') if isinstance(m, str)]

a = Analysis(
    ['pdf_generator_ui.py'],
    pathex=[],
    binaries=numpy_dlls,
    datas=datas,
    hiddenimports=[
        # --- Local Web Server framework ---
        'bottle',
        'web_assets',
        # --- Standard Tkinter (headless file dialgos) ---
        '_tkinter',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        # --- Core Excel / PDF ---
        'openpyxl',
        'openpyxl.styles',
        'pandas',
        'certifi',
        'pyexpat',
        '_elementtree',
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.platypus',
        'reportlab.lib.styles',
        'reportlab.lib.enums',
        'reportlab.pdfbase',
        'reportlab.pdfbase.pdfmetrics',
        'reportlab.pdfbase.ttfonts',
        'reportlab.lib.colors',
        # --- App modules ---
        'pdf_logic',
        'equitas_logic',
        # --- Required by pyi_rth_multiprocessing runtime hook ---
        'select',
        'selectors',
        '_multiprocessing',
        'multiprocessing',
        'multiprocessing.reduction',
    ] + np_extra,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'tensorflow', 'keras', 'scipy', 'transformers', 'cv2',
        'sklearn', 'seaborn', 'matplotlib', 'sqlalchemy', 'botocore',
        'boto3', 'aiohttp', 'httpx', 'jinja2', 'sympy',
    ],
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
    name='Audit_Engine_Elite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity='-',
    entitlements_file=None,
    icon=None,
)