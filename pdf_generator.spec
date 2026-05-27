# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

numpy_dlls = collect_dynamic_libs('numpy')

# Static assets (UI)
ui_static = os.path.join('src', 'audit_engine', 'ui', 'static')
datas = [
    ('fonts', 'fonts'),
    (ui_static, 'audit_engine/ui/static'),
] + collect_data_files('certifi') + collect_data_files('webview')

def safe_collect_submodules(package_name):
    try:
        return [m for m in collect_submodules(package_name) if isinstance(m, str)]
    except Exception:
        return []

np_extra = safe_collect_submodules('numpy.random')
webview_extra = safe_collect_submodules('webview')
comtypes_extra = safe_collect_submodules('comtypes')

a = Analysis(
    ['src/audit_engine/__main__.py'],
    pathex=['src'],
    binaries=numpy_dlls,
    datas=datas,
    hiddenimports=[
        # --- Vendored WSGI ---
        'audit_engine.lib',
        'audit_engine.lib.bottle',
        # --- Core package ---
        'audit_engine',
        'audit_engine._version',
        'audit_engine.database',
        'audit_engine.database.legacy',
        'audit_engine.exceptions',
        'audit_engine.tasks.workers',
        'audit_engine.tasks.tracker',
        # --- Web layer ---
        'audit_engine.web',
        'audit_engine.web.routes',
        # --- Services ---
        'audit_engine.services',
        'audit_engine.services.idfc',
        'audit_engine.services.equitas',
        'audit_engine.services.arvog',
        # --- Updater ---
        'audit_engine.updater',
        'audit_engine.updater.client',
        # --- Utils ---
        'audit_engine.utils',
        'audit_engine.utils.config',
        'audit_engine.utils.platform',
        'audit_engine.utils.dialogs',
        # --- PyWebView ---
        'webview',
        'webview.platforms',
        'webview.platforms.cocoa',
        'webview.platforms.edgechromium',
        'webview.platforms.gtk',
        'webview.platforms.qt',
        'gi',
        # --- Tkinter (file dialogs) ---
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
        # --- Stdlib used by updater ---
        'tarfile',
        'hashlib',
        'json',
        'ssl',
        # --- multiprocessing ---
        'select',
        'selectors',
        '_multiprocessing',
        'multiprocessing',
        'multiprocessing.reduction',
    ] + np_extra + webview_extra + comtypes_extra,
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

is_mac = (sys.platform == 'darwin')

if is_mac:
    # On macOS, use ONEDIR mode inside a proper .app bundle for maximum performance & Gatekeeper safety
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Audit_Engine_Elite',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=True,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name='Audit_Engine_Elite_Dir',
    )
    app = BUNDLE(
        coll,
        name='Audit_Engine_Elite.app',
        icon=None,
        bundle_identifier='com.auditengine.elite',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
        }
    )
else:
    # On Windows/Linux, use ONEFILE mode for a single self-contained portable executable
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
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )
