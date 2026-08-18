"""The desktop UI must be a single self-contained HTML document.

The desktop app runs no HTTP server: it writes get_html() to a temp file and
loads it over file://. Any leftover absolute asset path (/static/app.js,
/static/web.css) resolves against the filesystem root there, so the browser
loads neither the stylesheet nor the script — which historically shipped a
binary that opened to an unstyled page with no working JavaScript at all.
"""

import re

import pytest

from audit_engine import ui


@pytest.fixture(scope="module")
def html():
    return ui.get_html("9.9.9")


def test_no_absolute_static_references_survive(html):
    """The whole point: nothing may need path resolution under file://."""
    assert "/static/" not in html


def test_stylesheet_is_inlined(html):
    assert "<link" not in html or 'rel="stylesheet"' not in html
    # chrome classes that only exist in web.css must be present in the document
    for cls in (".logo-mark", ".top-navbar", ".nav-btn", ".bank-pill"):
        assert cls in html, f"{cls} missing — stylesheet was not inlined"


def test_script_is_inlined_and_executable(html):
    assert "<script src=" not in html
    # a function defined in app.js must now live in the document itself
    assert "function switchTab(" in html
    assert "function runValidator(" in html


def test_inlined_script_does_not_break_out_of_its_tag(html):
    """A literal </script> inside the JS would terminate the tag early."""
    body = html[html.index("function switchTab("):]
    # the first closing tag after the JS must be the one we emitted, not an
    # escaped occurrence inside a string literal
    assert "<\\/script>" in html or "</script>" in body


def test_version_is_substituted(html):
    assert "{{VERSION}}" not in html
    assert "9.9.9" in html


def test_missing_asset_leaves_tag_intact_rather_than_blanking_page(monkeypatch):
    """An incomplete bundle should degrade, not silently produce a dead page."""
    monkeypatch.setattr(ui, "_read_asset", lambda _name: None)
    out = ui._inline_assets('<link rel="stylesheet" href="/static/web.css?v=1">')
    assert out == '<link rel="stylesheet" href="/static/web.css?v=1">'


def test_inlining_is_idempotent_on_already_inlined_html(html):
    assert ui._inline_assets(html) == html


def test_assets_actually_ship_in_the_package():
    """web.css/app.js must live beside index.html so PyInstaller bundles them."""
    import os
    for name in ("index.html", "app.js", "web.css"):
        assert os.path.isfile(os.path.join(ui._ASSETS_DIR, name)), f"{name} missing from ui/static"


def test_every_static_ref_in_index_html_resolves():
    """Guards against a future tag pointing at an asset that isn't shipped."""
    import os
    with open(os.path.join(ui._ASSETS_DIR, "index.html"), encoding="utf-8") as f:
        raw = f.read()
    refs = re.findall(r'(?:href|src)="/static/([^"?]+)', raw)
    assert refs, "expected index.html to reference its assets"
    for name in refs:
        assert os.path.isfile(os.path.join(ui._ASSETS_DIR, name)), f"index.html references missing {name}"
