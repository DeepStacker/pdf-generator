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
    for cls in (".logo-mark", ".sidebar", ".nav-btn", ".bank-pill"):
        assert cls in html, f"{cls} missing — stylesheet was not inlined"


def test_script_is_inlined_and_executable(html):
    assert "<script src=" not in html
    # a function defined in app.js must now live in the document itself
    assert "function switchTab(" in html
    assert "function runValidator(" in html
    assert "function switchArvogPanel(" in html
    assert "async function runArvogRebuild(" in html


def test_no_element_id_is_declared_twice(html):
    """getElementById returns the first match, so a repeat is unreachable.

    arvogAutoOpen and eqAutoOpen were each declared twice: the listener bound
    to one copy and the run read the other, which never saw the update.
    """
    import re
    from collections import Counter

    counts = Counter(re.findall(r'\bid="([^"]+)"', html))
    repeated = sorted(i for i, n in counts.items() if n > 1)
    assert not repeated, f"ids declared more than once: {repeated}"


def test_every_inline_handler_has_a_function(html):
    """An onclick naming a function that was never written throws on click.

    Two shipped that way: the History search's clear button called
    clearSearch(), and selecting Consolidation called loadConsolidationBanks().
    """
    import re

    called = set()
    for attr in re.findall(r'on(?:click|input|change)="([^"]+)"', html):
        # Bare calls only — `document.getElementById(...)` is a method on an
        # object, not a name this document has to define.
        for name in re.findall(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(", attr):
            called.add(name)

    defined = set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", html))
    defined |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(", html))

    builtins = {
        "alert", "confirm", "event", "parseInt", "parseFloat", "String", "Number",
        "encodeURIComponent", "decodeURIComponent", "setTimeout", "JSON",
    }
    missing = sorted(called - defined - builtins)
    assert not missing, f"inline handlers call undefined functions: {missing}"


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


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = lin(r), lin(g), lin(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    la, lb = max(la, lb), min(la, lb)
    return (la + 0.05) / (lb + 0.05)


def test_solid_button_fills_pass_wcag_aa_with_white_text():
    """A button whose fill and text read as the same weight is unusable.

    Every one of these hexes is a *solid, full-opacity* background this app
    draws white bold text over -- Generate Reports, a segmented control's
    selected state, Stop, the update banner. Text this size (well under the
    18pt/14pt-bold WCAG "large text" threshold) needs 4.5:1 against its
    background; #34C98C, the accent-emerald shade these were themed from
    before this test existed, measured 2.1:1 here — a button whose label was,
    for practical purposes, invisible.
    """
    fills = {
        "btn-primary / IDFC fill":      "506CDB",
        "btn-success / Arvog fill":     "18855B",
        "Equitas fill":                 "9F6A19",
        "bg-blue-600":                  "4768F0",
        "bg-emerald-600":               "18855B",
        "bg-rose-600 (Stop/danger)":    "D43D47",
    }
    failing = {
        name: round(_contrast_ratio("FFFFFF", hex_val), 2)
        for name, hex_val in fills.items()
        if _contrast_ratio("FFFFFF", hex_val) < 4.5
    }
    assert not failing, f"white text fails AA against these fills: {failing}"


def test_dim_text_tier_is_readable_on_the_canvas():
    """--text-dim / .text-slate-600 are used for real captions and labels,
    not just decoration, so they need the same 4.5:1 floor as body text."""
    ratio = _contrast_ratio("717B89", "0A0D12")
    assert ratio >= 4.5, f"text-dim only reaches {ratio:.2f}:1 against the canvas"


def test_every_wh_size_class_used_is_defined(html):
    """An SVG icon sized with .w-7.h-7 rendered at roughly ten times its
    intended size -- neither class exists in this file's hand-rolled utility
    set (only w-3/4/5/8/12/20/44/64 do), so the browser fell back to the
    element's unconstrained intrinsic size. Four icons shipped that way
    before this was caught by eye rather than by a test.
    """
    defined_w = set(re.findall(r'\.w-(\d+(?:\\\.\d+)?)\s*\{', html))
    defined_h = set(re.findall(r'\.h-(\d+(?:\\\.\d+)?)\s*\{', html))

    body = html[html.index("<body"):]
    missing = set()
    for m in re.finditer(r'class="([^"]*)"', body):
        classes = m.group(1).split()
        for cls in classes:
            mw = re.fullmatch(r"w-(\d+)", cls)
            if mw and mw.group(1) not in defined_w:
                missing.add(cls)
            mh = re.fullmatch(r"h-(\d+)", cls)
            if mh and mh.group(1) not in defined_h:
                missing.add(cls)

    assert not missing, f"used but never defined -- would render unconstrained: {sorted(missing)}"


def test_desktop_detection_does_not_race_the_pywebview_bridge(html):
    """Desktop/web mode must be decided from the URL, not from window.pywebview.

    pywebview injects window.pywebview asynchronously. Measured on macOS:
    it is still undefined when DOMContentLoaded fires at t=11ms, and the
    pywebviewready event does not arrive until t=110ms. isWebMode() used to
    be `!window.pywebview`, so at startup the desktop app called itself a
    browser and hid its own Browse button and auto-open checkbox -- leaving
    no way at all to set the output folder, since that field is readonly.
    The paired 100ms readiness timeout lost the same race by 10ms, sending
    the first /api/dashboard call to file:///api/dashboard, which cannot
    answer: the saved output path was never applied and every stat tile kept
    its 'Loading...' placeholder for the life of the session.

    The document is served over file:// by the desktop shell and over
    http(s) by both web front ends, so the protocol answers this
    synchronously, before any bridge exists.
    """
    body = html[html.index("function isWebMode("):]
    impl = body[:body.index("}")]
    assert "window.pywebview" not in impl, (
        "isWebMode() is reading window.pywebview again -- it is undefined at "
        f"startup and the desktop app will misdetect itself as a browser: {impl!r}"
    )
    assert "IS_DESKTOP_SHELL" in impl

    assert "window.location.protocol === 'file:'" in html, (
        "the file:// check that makes desktop detection race-free is gone"
    )


def test_ipc_readiness_timeout_outlasts_the_handshake(html):
    """The desktop fallback timeout must not fire before pywebviewready.

    The bridge announced itself at 110ms in the measurement above; a 100ms
    give-up sent the app's first API call to a file:// URL. Browser mode
    still resolves fast because it has no bridge coming.
    """
    m = re.search(r"IS_DESKTOP_SHELL \? (\d+) : (\d+)", html)
    assert m, "the readiness timeout no longer distinguishes desktop from browser"
    desktop_ms, browser_ms = int(m.group(1)), int(m.group(2))
    assert desktop_ms >= 5000, f"desktop gives up after only {desktop_ms}ms"
    assert browser_ms <= 500, f"browser stalls {browser_ms}ms before its first call"


def test_every_static_ref_in_index_html_resolves():
    """Guards against a future tag pointing at an asset that isn't shipped."""
    import os
    with open(os.path.join(ui._ASSETS_DIR, "index.html"), encoding="utf-8") as f:
        raw = f.read()
    refs = re.findall(r'(?:href|src)="/static/([^"?]+)', raw)
    assert refs, "expected index.html to reference its assets"
    for name in refs:
        assert os.path.isfile(os.path.join(ui._ASSETS_DIR, name)), f"index.html references missing {name}"
