"""The two front ends must stay one design, not two that resemble each other.

The desktop app and the browser app drifted badly once already: the browser
build was still called "FinConsolidate PRO", navigated by a top tab bar
instead of the sidebar, and was styled with gradient text, neon glows and
glassmorphism that the desktop had dropped. Nothing failed when that
happened, because nothing checked.

So the palette and the component rules now live in exactly two files that
both apps read, and these tests fail if either app stops reading them or
starts re-inventing the look locally.
"""

import os
import re

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SHARED = os.path.join(_ROOT, "src", "audit_engine", "ui", "static")
_WEB_SRC = os.path.join(_ROOT, "web", "src")


def _web_sources() -> list[tuple[str, str]]:
    out = []
    for dirpath, _dirs, files in os.walk(_WEB_SRC):
        for name in files:
            if name.endswith((".tsx", ".ts", ".css")):
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as f:
                    out.append((os.path.relpath(path, _ROOT), f.read()))
    return out


@pytest.fixture(scope="module")
def web_index_css() -> str:
    with open(os.path.join(_WEB_SRC, "index.css"), encoding="utf-8") as f:
        return f.read()


def test_shared_stylesheets_exist():
    """Both apps read these two files; nothing works if they move."""
    for name in ("tokens.css", "web.css"):
        assert os.path.isfile(os.path.join(_SHARED, name)), f"{name} missing from ui/static"


def test_palette_lives_only_in_tokens_css():
    """web.css draws from the tokens; it must not redeclare them."""
    with open(os.path.join(_SHARED, "tokens.css"), encoding="utf-8") as f:
        tokens = f.read()
    with open(os.path.join(_SHARED, "web.css"), encoding="utf-8") as f:
        components = f.read()

    assert "--accent-blue-fill:" in tokens, "the palette is not in tokens.css"
    assert ":root" not in components, (
        "web.css declares its own :root block again -- the palette belongs in "
        "tokens.css so a colour cannot be changed for one app and not the other"
    )


def test_the_browser_app_imports_the_shared_design_system(web_index_css):
    """If this import goes, the browser app is free to drift again."""
    for name in ("tokens.css", "web.css"):
        assert f"src/audit_engine/ui/static/{name}" in web_index_css, (
            f"web/src/index.css no longer imports the shared {name}"
        )


def test_the_browser_app_does_not_reinvent_the_look():
    """The styling vocabulary the desktop deliberately dropped.

    Every one of these was in the browser build: gradient headline text, glow
    shadows behind panels, frosted-glass cards. The user's word for the result
    was "cocky", and asked for professional instead.
    """
    banned = {
        "bg-gradient-": "gradient fills",
        "bg-clip-text": "gradient text",
        "backdrop-blur": "frosted glass",
        "glass-panel": "the old glassmorphism panel",
        "neon-glow": "glow shadows",
    }
    offenders: dict[str, list[str]] = {}
    for path, text in _web_sources():
        for token, what in banned.items():
            if token in text:
                offenders.setdefault(f"{what} ({token})", []).append(path)
    assert not offenders, f"the browser app is re-inventing the look: {offenders}"


def test_the_browser_app_is_dark_only_like_the_desktop():
    """Light mode was a stack of !important overrides keyed on hex colours.

    It was dropped rather than ported, so any leftover reference to it is a
    control that does nothing or a style that can never apply.
    """
    offenders = [path for path, text in _web_sources() if "light-mode" in text]
    assert not offenders, f"light-mode handling survives in: {offenders}"


def test_both_apps_carry_the_same_name():
    """The browser build shipped as "FinConsolidate PRO" long after the rename."""
    with open(os.path.join(_ROOT, "web", "index.html"), encoding="utf-8") as f:
        web_html = f.read()
    assert "GSS-MIS" in web_html
    assert not re.search(r"FinConsolidate", web_html, re.I)

    stale = [path for path, text in _web_sources() if re.search(r"FinConsolidate", text, re.I)]
    assert not stale, f"old product name still in: {stale}"


def test_no_responsive_unhide_fights_the_shared_hidden_rule():
    """`hidden lg:block` cannot work in the browser app any more.

    The shared sheet declares `.hidden { display: none !important }` because
    the desktop toggles whole screens with it and needs it to beat every
    display utility on the element. Tailwind's responsive variants are plain
    rules, so `lg:block` loses to it and the element stays hidden at every
    width -- silently, since nothing errors. The validator's issues panel
    shipped that way and could never appear. Write `max-lg:hidden` instead.
    """
    pattern = re.compile(r'class(?:Name)?="[^"]*\bhidden\s+(?:sm|md|lg|xl|2xl):(?:block|flex|grid|inline|inline-block|table)\b')
    offenders = [path for path, text in _web_sources() if pattern.search(text)]
    assert not offenders, (
        f"these use `hidden <breakpoint>:<display>`, which the shared "
        f"!important .hidden defeats -- use max-<breakpoint>:hidden: {offenders}"
    )


def test_no_component_uses_a_style_class_nothing_defines():
    """A class that no stylesheet defines renders as nothing, silently.

    `glass-panel` outlived its definition here: panels carrying it drew no
    background or border at all, and it took a redesign to notice. These are
    the local classes the browser build used to define for itself before the
    shared sheet replaced them.
    """
    retired = ("glass-panel", "glass-panel-hover", "app-input", "custom-scrollbar", "neon-glow-blue",
               "neon-glow-emerald", "neon-glow-rose")
    with open(os.path.join(_WEB_SRC, "index.css"), encoding="utf-8") as f:
        index_css = f.read()
    with open(os.path.join(_SHARED, "web.css"), encoding="utf-8") as f:
        shared_css = f.read()

    offenders: dict[str, list[str]] = {}
    for name in retired:
        if f".{name}" in index_css or f".{name}" in shared_css:
            continue  # still defined somewhere, so using it is fine
        for path, text in _web_sources():
            if path.endswith("index.css"):
                continue
            if re.search(rf'\b{re.escape(name)}\b', text):
                offenders.setdefault(name, []).append(path)
    assert not offenders, f"used but no longer defined by any stylesheet: {offenders}"


def test_the_browser_app_is_usable_on_a_phone(web_index_css):
    """The shared sheet is desktop-first below 768px, and that is wrong here.

    It narrows the sidebar to a 64px icon rail and hides
    .sidebar-item-label -- which leaves the four banks as four unlabelled
    coloured dots, with no way to tell IDFC from Arvog. It also *shrinks*
    buttons and chips to 0.65rem on the smallest screens, where targets need
    to grow: ten of twenty-five buttons measured under the 44px touch floor.

    So the browser app replaces that behaviour outright with a drawer, and
    these are the pieces it cannot lose.
    """
    assert "@media (max-width: 860px)" in web_index_css, "the mobile layer is gone"

    mobile = web_index_css[web_index_css.index("@media (max-width: 860px)"):]

    # the rail is replaced by a drawer, not merely narrowed
    assert ".sidebar.is-open" in mobile, "no drawer open state"
    assert ".sidebar-backdrop" in mobile, "a drawer with no backdrop traps the user"
    assert ".mobile-topbar" in mobile, "nothing opens the drawer"

    # the labels must come back -- an unnamed dot is not navigation
    assert ".sidebar-item-label" in mobile and "revert" in mobile, (
        "the shared sheet hides .sidebar-item-label below 768px; the mobile "
        "layer has to put it back or the banks are unlabelled dots again"
    )

    # and targets grow rather than shrink
    assert "min-height: 44px" in mobile, "no 44px touch floor declared"
