"""Frontend asset loader — returns the SPA HTML with version injected."""

import os

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "static")


def get_html(version: str = "5.2.217") -> str:
    """Read index.html and inject the version string."""
    path = os.path.join(_ASSETS_DIR, "index.html")
    with open(path, encoding="utf-8") as f:
        return f.read().replace("{{VERSION}}", version)
