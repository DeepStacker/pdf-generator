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

# --- Linux runtime module collection (GIO, GdkPixbuf, GTK theme, GLib schemas) ---
if sys.platform == 'linux':
    import glob as _glob
    # GIO modules (TLS, proxy, etc.)
    _gio_dir = '/usr/lib/x86_64-linux-gnu/gio/modules'
    if os.path.isdir(_gio_dir):
        for _f in _glob.glob(os.path.join(_gio_dir, '*.so')):
            datas.append((_f, 'gio/modules'))
    # GdkPixbuf loader modules (png, svg, etc.)
    _pixbuf_dir = '/usr/lib/x86_64-linux-gnu/gdk-pixbuf-2.0/2.10.0/loaders'
    if os.path.isdir(_pixbuf_dir):
        for _f in _glob.glob(os.path.join(_pixbuf_dir, '*.so')):
            datas.append((_f, 'gdk-pixbuf-loaders'))
    # GTK immodules (input methods)
    _gtk_im_dir = '/usr/lib/x86_64-linux-gnu/gtk-3.0/3.0.0/immodules'
    if os.path.isdir(_gtk_im_dir):
        for _f in _glob.glob(os.path.join(_gtk_im_dir, '*.so')):
            datas.append((_f, 'gtk-immodules'))
    # Pango modules
    _pango_mod_dir = '/usr/lib/x86_64-linux-gnu/pango/1.8.0/modules'
    if os.path.isdir(_pango_mod_dir):
        for _f in _glob.glob(os.path.join(_pango_mod_dir, '*.so')):
            datas.append((_f, 'pango/modules'))
    # GTK theme (Adwaita — default GTK theme)
    _theme_dir = '/usr/share/themes/Adwaita'
    if os.path.isdir(_theme_dir):
        datas.append((_theme_dir, 'share/themes/Adwaita'))
    # GLib schemas (GSettings)
    _schema_dir = '/usr/share/glib-2.0/schemas'
    if os.path.isdir(_schema_dir):
        datas.append((_schema_dir, 'share/glib-2.0/schemas'))
    # Cache files generated in CI
    _pixbuf_cache = os.path.join(os.path.dirname(__file__), 'gdk-pixbuf-loaders.cache')
    if os.path.isfile(_pixbuf_cache):
        datas.append((_pixbuf_cache, 'gdk-pixbuf-loaders.cache'))
    _gtk_im_cache = os.path.join(os.path.dirname(__file__), 'gtk-immodules.cache')
    if os.path.isfile(_gtk_im_cache):
        datas.append((_gtk_im_cache, 'gtk-immodules.cache'))

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
        'gi._enum',
        'gi.repository.GIRepository',
        'gi.repository.WebKit2',
        'gi.repository.Soup',
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
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['hooks/runtime_hook_linux.py'],
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
