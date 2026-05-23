# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# Try to find TCL/TK paths to ensure they are bundled
tcl_lib_path = ""
tk_lib_path = ""

if sys.platform == "win32":
    base_path = os.path.dirname(sys.executable)
    possible_tcl = os.path.join(base_path, 'tcl')
    if os.path.exists(possible_tcl):
        for item in os.listdir(possible_tcl):
            if item.startswith('tcl8'):
                tcl_lib_path = os.path.join(possible_tcl, item)
            if item.startswith('tk8'):
                tk_lib_path = os.path.join(possible_tcl, item)

datas = [('fonts', 'fonts')] + collect_data_files('certifi')
if tcl_lib_path and tk_lib_path:
    datas.append((tcl_lib_path, os.path.join('tcl', os.path.basename(tcl_lib_path))))
    datas.append((tk_lib_path, os.path.join('tk', os.path.basename(tk_lib_path))))

# Collect all numpy dynamic libs (.pyd files) and their submodules
numpy_dlls = collect_dynamic_libs('numpy')
# Also collect numpy.random submodules that are commonly missed
np_extra = [m for m in collect_submodules('numpy.random') if isinstance(m, str)]

a = Analysis(
    ['pdf_generator_ui.py'],
    pathex=[],
    binaries=numpy_dlls,
    datas=datas,
    hiddenimports=[
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.ttk',
        'openpyxl',
        'openpyxl.styles',
        'pandas',
        'certifi',
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
        'pdf_logic',
        'equitas_logic',
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity='-',
    entitlements_file=None,
    icon=None,
)