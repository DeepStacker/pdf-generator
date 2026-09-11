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
    # the palette is its own asset now and must be inlined too, not just linked
    assert "--accent-blue-fill" in html, "tokens.css was not inlined"
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
    for name in ("index.html", "app.js", "web.css", "tokens.css"):
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


def test_every_class_used_is_defined_somewhere(html):
    """A class the stylesheet never defines does nothing, silently.

    This has shipped twice. An SVG sized with .w-7.h-7 rendered at roughly
    ten times its intended size, because neither class exists in this file's
    hand-rolled utility set and the browser fell back to the element's
    unconstrained intrinsic size. Separately, .enterprise-panel sat on seven
    Consolidation cards that had therefore never drawn a background or a
    border at all. Both were caught by eye, months apart.

    So this checks every class in the document, not just the sizing ones,
    against the CSS that actually ships -- which means the fully inlined
    output, since web.css is a separate file until get_html() folds it in.
    """
    style_text = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))
    body = html[html.index("<body"):]

    def css_escape(name: str) -> str:
        return "".join("\\" + ch if ch in "/:.[]" else ch for ch in name)

    # Painted by updateThemeBranding() as inline styles per active bank, so
    # they are markers for JavaScript rather than selectors CSS has to carry.
    js_markers = {
        "dynamic-accent-bg", "dynamic-accent-fg",
        "dynamic-accent-border", "dynamic-accent-stroke",
    }
    # Toggled at runtime; 'hidden' is the one of these the stylesheet does define.
    runtime = {"hidden", "active", "selected"}

    used = set()
    for m in re.finditer(r'class="([^"]*)"', body):
        used.update(m.group(1).split())

    missing = sorted(
        cls for cls in used
        if cls not in js_markers
        and cls not in runtime
        # class="${tone} ..." inside a JS template literal is a placeholder,
        # not a class name this document has to define.
        and not cls.startswith("${")
        and style_text.find("." + css_escape(cls)) == -1
    )
    assert not missing, f"used in markup but never defined in CSS: {missing}"


def test_a_finished_run_offers_a_way_to_start_the_next_one(html):
    """Completion used to be a dead end.

    setUiGeneratingState(false) re-enables the button but leaves the finished
    batch's files, console and progress ring in place, and loadDashboardData()
    restores that same checklist from config -- so pressing Generate again
    just rebuilt the masters that had already been built. The summary modal
    is the one thing every run ends on, so the reset lives there.
    """
    assert "function startNewRun(" in html
    assert 'id="summaryNewRunBtn"' in html
    assert 'onclick="startNewRun()"' in html

    # the updater reuses this modal for its restart notice, where restarting a
    # generation makes no sense -- the button is opt-in per call site
    assert "function openSummaryModal(summaryData, allowNewRun = false)" in html
    assert "openSummaryModal(data.summary, true)" in html


def test_bulk_selection_says_files_are_not_merged(html):
    """Every worker loops the batch one master at a time into its own folder.

    Nothing on screen said so, which left a bulk drop looking like it might
    merge the masters into a single report.
    """
    for prefix in ("idfc", "eq", "arvog"):
        assert f'id="{prefix}BulkHint"' in html, f"{prefix} has no bulk hint"
    assert "each processed separately" in html


def test_every_static_ref_in_index_html_resolves():
    """Guards against a future tag pointing at an asset that isn't shipped."""
    import os
    with open(os.path.join(ui._ASSETS_DIR, "index.html"), encoding="utf-8") as f:
        raw = f.read()
    refs = re.findall(r'(?:href|src)="/static/([^"?]+)', raw)
    assert refs, "expected index.html to reference its assets"
    for name in refs:
        assert os.path.isfile(os.path.join(ui._ASSETS_DIR, name)), f"index.html references missing {name}"


def test_the_toast_overflow_loop_removes_synchronously(html):
    """A deferred removal inside this loop never ends it.

    showToast trims the queue with `while (container.children.length >=
    TOAST_MAX_VISIBLE)`. That condition is re-read every pass, so removing
    the oldest toast on a 200ms timer leaves the count unchanged and the
    loop spins forever -- it froze the whole window on the fourth toast of a
    batch. A merge that reports three skipped branches and then succeeds is
    exactly four, and that is how it was found.
    """
    start = html.index("while (container.children.length")
    body = html[html.index("{", start) + 1:]
    body = body[:body.index("}")]

    assert "setTimeout" not in body, (
        "the toast overflow loop defers its removal, so its own condition "
        "never changes and the window hangs"
    )
    assert ".remove()" in body
