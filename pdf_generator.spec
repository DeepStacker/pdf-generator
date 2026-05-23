# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import glob
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# Collect dynamic libs (.pyd/.so) from numpy only (others are auto-detected)
dlls = collect_dynamic_libs('numpy')

# On Windows, explicitly bundle Tcl/Tk DLLs so _tkinter.pyd can load them
tk_dlls = []
if sys.platform == "win32":
    py_root = os.path.dirname(sys.executable)
    # Look in DLLs folder (official Python) and bin folder (some distributions)
    for search_dir in [os.path.join(py_root, 'DLLs'), os.path.join(py_root, 'bin')]:
        if os.path.isdir(search_dir):
            for dll_pattern in ['tcl*.dll', 'tk*.dll']:
                tk_dlls.extend(glob.glob(os.path.join(search_dir, dll_pattern)))
    # Also try the tcl/tk library directories
    tcl_dir = os.path.join(py_root, 'tcl')
    if os.path.isdir(tcl_dir):
        for entry in os.listdir(tcl_dir):
            lib_dir = os.path.join(tcl_dir, entry)
            if os.path.isdir(lib_dir):
                for dll_pattern in ['*.dll', '*.so']:
                    tk_dlls.extend(glob.glob(os.path.join(lib_dir, dll_pattern)))
    dlls.extend((dll, '.') for dll in tk_dlls if os.path.isfile(dll))

datas = [('fonts', 'fonts')] + collect_data_files('certifi')


def safe_submodules(pkg):
    """Collect submodules, filtering out any non-string entries."""
    try:
        return [m for m in collect_submodules(pkg) if isinstance(m, str)]
    except Exception:
        return []


# Collect ALL submodules from our major dependencies
pkg_imports = []
for pkg in ['numpy', 'pandas', 'openpyxl', 'reportlab', 'PIL']:
    pkg_imports.extend(safe_submodules(pkg))

# Standard library C extensions that PyInstaller frequently misses on Windows
stdlib_extensions = [
    'pyexpat',
    '_elementtree',
    '_socket',
    '_ssl',
    '_hashlib',
    '_multiprocessing',
    '_csv',
    '_json',
    '_datetime',
    '_decimal',
    '_ctypes',
    '_zlib',
    '_bz2',
    '_lzma',
]

a = Analysis(
    ['pdf_generator_ui.py'],
    pathex=[],
    binaries=dlls,
    datas=datas,
    hiddenimports=[
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.ttk',
        'openpyxl',
        'pandas',
        'certifi',
        'reportlab',
        'pdf_logic',
        'equitas_logic',
    ] + pkg_imports + stdlib_extensions,
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