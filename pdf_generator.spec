# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# ============================================================
# Windows DLL collection
# ============================================================
# This section ensures ALL runtime dependencies are bundled inside the
# single-file executable so it works on ANY Windows machine — including:
#   - Parallels Desktop (Windows ARM64 emulating x86_64)
#   - Locked-down corporate PCs without admin rights
#   - Fresh Windows installs without VC++ Redistributable
#   - Windows Sandbox / VMs
# ============================================================
extra_dlls = []
tk_datas = []

if sys.platform == "win32":
    import glob

    # --- 1. Discover search directories ---
    _bases = set()
    for _b in [os.path.dirname(sys.executable),
               sys.prefix,
               getattr(sys, 'base_prefix', sys.prefix),
               sys.exec_prefix]:
        if _b:
            _bases.add(os.path.normpath(_b))

    _search_dirs = []
    for _base in _bases:
        for _sub in ['.', 'DLLs', 'bin', 'libs',
                     'Library\\bin', 'Library\\lib']:
            _d = os.path.normpath(os.path.join(_base, _sub))
            if os.path.isdir(_d) and _d not in _search_dirs:
                _search_dirs.append(_d)

    # --- 2. Collect ALL required DLLs ---
    # python312.dll depends on vcruntime140.dll + vcruntime140_1.dll
    # _tkinter.pyd depends on tcl86t.dll + tk86t.dll
    # Tcl depends on zlib1.dll
    # We bundle everything so the exe is fully self-contained.
    _dll_patterns = [
        'python3*.dll',        # Python runtime DLL
        'vcruntime*.dll',      # Visual C++ runtime
        'msvcp*.dll',          # MSVC C++ standard library
        'ucrtbase*.dll',       # Universal C runtime (usually OS-provided but bundle just in case)
        'tcl*.dll',            # Tcl library
        'tk*.dll',             # Tk library
        'zlib*.dll',           # Compression library
        'libcrypto*.dll',      # OpenSSL (for HTTPS/certifi)
        'libssl*.dll',         # OpenSSL
        'libffi*.dll',         # ctypes FFI
        'sqlite3*.dll',        # SQLite (if used by any dependency)
    ]
    for _sd in _search_dirs:
        for _pat in _dll_patterns:
            for _f in glob.glob(os.path.join(_sd, _pat)):
                if _f not in extra_dlls:
                    extra_dlls.append(_f)

    # Fallback: recursive search if critical DLLs weren't found
    _found_names = {os.path.basename(d).lower() for d in extra_dlls}
    _critical = ['vcruntime140.dll', 'python312.dll']
    _missing_critical = [c for c in _critical if c not in _found_names]
    if _missing_critical:
        print(f"[spec] Critical DLLs not found in standard paths: {_missing_critical}")
        print(f"[spec] Running fallback recursive search...")
        for _base in _bases:
            for _root, _dirs, _files in os.walk(_base):
                for _f in _files:
                    if _f.lower() in _missing_critical:
                        _fp = os.path.join(_root, _f)
                        if _fp not in extra_dlls:
                            extra_dlls.append(_fp)
                            print(f"[spec]   Found: {_fp}")

    # --- 3. Tcl/Tk library data files (init.tcl, pkgIndex.tcl, etc.) ---
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

    # --- 4. Summary ---
    print(f"[spec] Bundling {len(extra_dlls)} DLL(s):")
    for d in sorted(extra_dlls):
        print(f"  {os.path.basename(d):30s}  ({d})")
    if tk_datas:
        print(f"[spec] Bundling {len(tk_datas)} Tcl/Tk data dir(s):")
        for src, dst in tk_datas:
            print(f"  {dst}")

    # Verify critical DLLs were found
    _found_names = {os.path.basename(d).lower() for d in extra_dlls}
    for _c in ['vcruntime140.dll']:
        if _c not in _found_names:
            print(f"[spec] *** CRITICAL WARNING: {_c} NOT FOUND! ***")
            print(f"[spec] *** The exe will CRASH on machines without VC++ runtime! ***")


numpy_dlls = collect_dynamic_libs('numpy')
dll_entries = [(d, '.') for d in extra_dlls]
all_dlls = numpy_dlls + dll_entries

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
    upx=False,                   # CRITICAL: UPX corrupts python312.dll on some Windows configs
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