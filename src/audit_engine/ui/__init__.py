"""Frontend asset loader — returns the SPA as one self-contained HTML document.

The desktop app does not run an HTTP server (Zero-Socket IPC): it writes this
HTML to a temp file and loads it over ``file://``. Under that scheme the
document's absolute asset paths (``/static/web.css``, ``/static/app.js``)
resolve against the *filesystem root*, not the app bundle, so the browser
silently loads neither — leaving an unstyled page with no JavaScript at all.

So the stylesheet and script are inlined here instead of being linked. The
result needs no path resolution, no static route, and no server, which is what
makes it work identically from a temp dir, a read-only bundle, or a UNC path.
"""

import os
import re

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "static")

# <link rel="stylesheet" href="/static/web.css?v=..."> (attribute order varies)
_CSS_LINK_RE = re.compile(r"""<link\b[^>]*href=["']/static/(?P<name>[^"'?]+)(?:\?[^"']*)?["'][^>]*>""")
# <script src="/static/app.js?v=..."></script>
_SCRIPT_SRC_RE = re.compile(r"""<script\b[^>]*src=["']/static/(?P<name>[^"'?]+)(?:\?[^"']*)?["'][^>]*>\s*</script>""")


def _read_asset(name: str) -> str | None:
    path = os.path.join(_ASSETS_DIR, name)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def _inline_assets(html: str) -> str:
    """Replace /static/ <link> and <script src> tags with their file contents.

    A missing asset leaves the original tag untouched rather than blanking the
    page, so an incomplete bundle degrades instead of failing silently.
    """
    def css_sub(m: re.Match) -> str:
        css = _read_asset(m.group("name"))
        return f"<style>\n{css}\n</style>" if css is not None else m.group(0)

    def js_sub(m: re.Match) -> str:
        js = _read_asset(m.group("name"))
        if js is None:
            return m.group(0)
        # </script> inside a string literal would close this tag early.
        return "<script>\n" + js.replace("</script>", "<\\/script>") + "\n</script>"

    html = _CSS_LINK_RE.sub(css_sub, html)
    return _SCRIPT_SRC_RE.sub(js_sub, html)


def get_html(version: str = "5.2.217") -> str:
    """Return the SPA HTML with the version injected and assets inlined."""
    path = os.path.join(_ASSETS_DIR, "index.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    return _inline_assets(html).replace("{{VERSION}}", version)
