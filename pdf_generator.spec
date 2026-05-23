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


def safe_submodules(pkg):
    """Collect submodules, filtering out any non-string entries."""
    try:
        return [m for m in collect_submodules(pkg) if isinstance(m, str)]
    except Exception:
        return []


# Collect dynamic libs (.pyd/.so) from all dependencies
dlls = []
for pkg in ['numpy', 'pandas', 'openpyxl', 'reportlab', 'PIL', 'charset_normalizer',
            'et_xmlfile', 'dateutil']:
    dlls.extend(collect_dynamic_libs(pkg))

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