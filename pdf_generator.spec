# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# ============================================================
# Tcl/Tk DLL and data collection (Windows)
# ============================================================
# _tkinter.pyd depends on tcl86t.dll, tk86t.dll, and possibly zlib1.dll.
# We also need the Tcl/Tk library directories (init.tcl etc.) as data.
tk_dlls = []
tk_datas = []

if sys.platform == "win32":
    import glob

    # Build a comprehensive set of directories to search for DLLs.
    # actions/setup-python, user installs, and venvs all have different layouts.
    _bases = set()
    for _b in [os.path.dirname(sys.executable),
               sys.prefix,
               getattr(sys, 'base_prefix', sys.prefix),
               sys.exec_prefix]:
        if _b:
            _bases.add(os.path.normpath(_b))

    _search_dirs = []
    for _base in _bases:
        for _sub in ['DLLs', 'bin', 'Library\\bin', 'Library\\lib', '.']:
            _d = os.path.normpath(os.path.join(_base, _sub))
            if os.path.isdir(_d) and _d not in _search_dirs:
                _search_dirs.append(_d)

    # Patterns for all DLLs that _tkinter.pyd needs at runtime
    _dll_patterns = ['tcl*.dll', 'tk*.dll', 'zlib*.dll']
    for _sd in _search_dirs:
        for _pat in _dll_patterns:
            tk_dlls.extend(glob.glob(os.path.join(_sd, _pat)))

    # Fallback: recursive search under all base directories
    if not any('tcl' in os.path.basename(d).lower() for d in tk_dlls):
        for _base in _bases:
            for _root, _dirs, _files in os.walk(_base):
                for _f in _files:
                    if _f.lower().endswith('.dll') and any(
                            _f.lower().startswith(p) for p in ('tcl', 'tk', 'zlib')):
                        tk_dlls.append(os.path.join(_root, _f))

    # Deduplicate
    tk_dlls = list(set(tk_dlls))

    # ---- Tcl/Tk library data files (init.tcl, pkgIndex.tcl, etc.) ----
    # Without these, _tkinter.pyd loads but Tcl_Init() fails with:
    #   "Can't find a usable init.tcl"
    for _base in _bases:
        _tcl_root = os.path.join(_base, 'tcl')
        if os.path.isdir(_tcl_root):
            for _item in os.listdir(_tcl_root):
                _item_path = os.path.join(_tcl_root, _item)
                if os.path.isdir(_item_path):
                    tk_datas.append((_item_path, os.path.join('tcl', _item)))
            break
        # Alternative layout: Library/lib (conda/msys2)
        _lib_root = os.path.join(_base, 'Library', 'lib')
        if os.path.isdir(_lib_root):
            for _item in os.listdir(_lib_root):
                if _item.startswith(('tcl', 'tk')) and os.path.isdir(
                        os.path.join(_lib_root, _item)):
                    tk_datas.append(
                        (os.path.join(_lib_root, _item), os.path.join('tcl', _item)))
            if tk_datas:
                break

    # Debug: print what was found
    if tk_dlls:
        print(f"[spec] Found {len(tk_dlls)} Tcl/Tk DLL(s):")
        for d in sorted(set(tk_dlls)):
            print(f"  {d}")
    else:
        print("[spec] WARNING: No Tcl/Tk DLLs found!")
    if tk_datas:
        print(f"[spec] Found {len(tk_datas)} Tcl/Tk data dir(s):")
        for src, dst in tk_datas:
            print(f"  {src} -> {dst}")
    else:
        print("[spec] WARNING: No Tcl/Tk data directories found!")


numpy_dlls = collect_dynamic_libs('numpy')
tk_dll_entries = [(d, '.') for d in set(tk_dlls)]
all_dlls = numpy_dlls + tk_dll_entries

datas = [('fonts', 'fonts')] + collect_data_files('certifi') + tk_datas

# Only collect numpy.random submodules (proven safe)
np_extra = [m for m in collect_submodules('numpy.random') if isinstance(m, str)]

a = Analysis(
    ['pdf_generator_ui.py'],
    pathex=[],
    binaries=all_dlls,
    datas=datas,
    hiddenimports=[
        # --- Tkinter (GUI framework) ---
        '_tkinter',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.ttk',
        # --- Excel / PDF ---
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