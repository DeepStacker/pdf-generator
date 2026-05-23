# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# Try to find TCL/TK DLLs on Windows and bundle them as binaries so _tkinter loads
tk_dlls = []
if sys.platform == "win32":
    import glob
    search_dirs = [
        os.path.join(os.path.dirname(sys.executable), 'DLLs'),
        os.path.join(os.path.dirname(sys.executable), 'bin'),
        os.path.join(os.path.dirname(sys.executable), '..', 'DLLs'),
        os.path.join(os.path.dirname(sys.executable), '..', 'bin'),
    ]
    for sd in search_dirs:
        sd = os.path.normpath(sd)
        if os.path.isdir(sd):
            for pat in ['tcl*.dll', 'tk*.dll']:
                tk_dlls.extend(glob.glob(os.path.join(sd, pat)))
    # Fallback: search the entire Python tree
    if not tk_dlls:
        py_root = os.path.dirname(sys.executable)
        for root, dirs, files in os.walk(py_root):
            for f in files:
                if f.lower().startswith(('tcl', 'tk')) and f.lower().endswith('.dll'):
                    tk_dlls.append(os.path.join(root, f))

numpy_dlls = collect_dynamic_libs('numpy')
# format_binaries_and_datas expects 2-element (src, dest_dir) tuples
tk_dll_entries = [(d, '.') for d in tk_dlls]
all_dlls = numpy_dlls + tk_dll_entries

datas = [('fonts', 'fonts')] + collect_data_files('certifi')

# Only collect numpy.random submodules (proven safe)
np_extra = [m for m in collect_submodules('numpy.random') if isinstance(m, str)]

a = Analysis(
    ['pdf_generator_ui.py'],
    pathex=[],
    binaries=all_dlls,
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