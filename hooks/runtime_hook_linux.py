import os
import sys
import tempfile

base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))

# GI typelib path
os.environ.setdefault('GI_TYPELIB_PATH', os.path.join(base_path, 'girepository-1.0'))

# GIO modules (TLS, proxy, etc.)
gio_mod_dir = os.path.join(base_path, 'gio', 'modules')
if os.path.isdir(gio_mod_dir):
    os.environ['GIO_MODULE_DIR'] = gio_mod_dir

# GdkPixbuf loaders — substitute @MEIPASS@ placeholder with real path
pixbuf_cache = os.path.join(base_path, 'gdk-pixbuf-loaders.cache')
if os.path.isfile(pixbuf_cache):
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.cache', delete=False)
    with open(pixbuf_cache) as f:
        content = f.read().replace('@MEIPASS@', base_path)
    tmp.write(content)
    tmp.close()
    os.environ['GDK_PIXBUF_MODULE_FILE'] = tmp.name

# GTK immodules — same placeholder substitution
gtk_im_cache = os.path.join(base_path, 'gtk-immodules.cache')
if os.path.isfile(gtk_im_cache):
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.cache', delete=False)
    with open(gtk_im_cache) as f:
        content = f.read().replace('@MEIPASS@', base_path)
    tmp.write(content)
    tmp.close()
    os.environ['GTK_IM_MODULE_FILE'] = tmp.name

# GTK data prefix — find themes, icons, schemas
gtk_share = os.path.join(base_path, 'share')
if os.path.isdir(gtk_share):
    os.environ['GTK_DATA_PREFIX'] = base_path
    os.environ['GTK_EXE_PREFIX'] = base_path
    os.environ.setdefault('XDG_DATA_DIRS', gtk_share)

# GSettings schema directory
gschema_dir = os.path.join(base_path, 'share', 'glib-2.0', 'schemas')
if os.path.isdir(gschema_dir):
    os.environ['GSETTINGS_SCHEMA_DIR'] = gschema_dir

# Pango modules
pango_mod_dir = os.path.join(base_path, 'pango', 'modules')
if os.path.isdir(pango_mod_dir):
    os.environ['PANGO_LIBDIR'] = pango_mod_dir

# WebKit2GTK helper subprocess binaries — patched libwebkit2gtk-4.1.so expects
# them at /tmp/lib/x86_64-linux-gnu/webkit2gtk-4.1/ (was /usr/... before patching).
# Create a symlink from the patched location to the bundle's webkit2gtk-4.1/ dir.
webkit_src = os.path.join(base_path, 'webkit2gtk-4.1')
webkit_dst = '/tmp/lib/x86_64-linux-gnu/webkit2gtk-4.1'
if os.path.isdir(webkit_src):
    try:
        os.makedirs(os.path.dirname(webkit_dst), exist_ok=True)
        if os.path.islink(webkit_dst) or os.path.isdir(webkit_dst):
            os.unlink(webkit_dst)
        os.symlink(webkit_src, webkit_dst)
    except OSError:
        pass

# Prevent GTK from loading system modules we didn't bundle
os.environ['GTK_MODULES'] = ''
