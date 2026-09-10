"""The installable app must not become a place customers' files get kept.

The server goes to some length not to retain anything: an uploaded workbook
is deleted when its job ends, a generated report seconds after it is served,
and the run history no longer records who owned them. A service worker cache
is browser-side storage that survives all of that, so a worker that cached a
download would put back a copy of the exact data the server just destroyed --
on the device, and outliving every server-side guarantee.

So the worker is allowed the app shell and content-addressed build assets,
and nothing else.
"""

import json
import os
import re

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PUBLIC = os.path.join(_ROOT, "web", "public")


@pytest.fixture(scope="module")
def service_worker() -> str:
    with open(os.path.join(_PUBLIC, "sw.js"), encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    with open(os.path.join(_PUBLIC, "manifest.webmanifest"), encoding="utf-8") as f:
        return json.load(f)


def test_the_service_worker_refuses_api_traffic(service_worker):
    """Verified live too: three API calls left zero entries in the cache."""
    assert "/api/" in service_worker, "the worker no longer mentions /api/ at all"

    guard = re.search(
        r"if \(url\.pathname\.startsWith\('/api/'\)\) return;", service_worker
    )
    assert guard, (
        "the early return that keeps /api/ out of the cache is gone -- an "
        "uploaded workbook or a generated report could now be stored in the "
        "browser and outlive the server deleting it"
    )

    # and the bail-out has to come before anything that could put() a response
    assert service_worker.index("/api/") < service_worker.index("caches.open(CACHE).then((c) => c.put"), (
        "the /api/ guard no longer precedes the caching branches"
    )


def test_only_content_addressed_assets_are_cached(service_worker):
    """A hashed filename changes when its contents do, so a hit is never stale.

    Anything without that property has to be revalidated instead, which is why
    the shell is network-first.
    """
    assert "isImmutableAsset" in service_worker
    assert "'/assets/'" in service_worker
    assert "request.mode === 'navigate'" in service_worker, "the shell is no longer network-first"


def test_the_manifest_is_installable(manifest):
    """Chrome will not offer to install without these."""
    assert manifest["name"] and manifest["short_name"]
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"

    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert "192x192" in sizes and "512x512" in sizes, f"missing a required icon size: {sizes}"

    purposes = {icon.get("purpose") for icon in manifest["icons"]}
    assert "maskable" in purposes, (
        "no maskable icon -- a launcher that crops to a circle will shave the corners off"
    )


def test_every_icon_the_manifest_promises_actually_ships(manifest):
    for icon in manifest["icons"]:
        name = icon["src"].lstrip("/")
        assert os.path.isfile(os.path.join(_PUBLIC, name)), f"{name} is referenced but missing"


def test_the_server_serves_the_pwa_files_from_the_root():
    """A worker only controls the scope it is served from, so /sw.js must
    answer at the root -- and the route may not be a catch-all, which is how
    directory traversal gets in."""
    main = os.path.join(_ROOT, "audit_engine_web", "__main__.py")
    with open(main, encoding="utf-8") as f:
        src = f.read()

    assert "_ROOT_PWA_FILES" in src
    for name in ("manifest.webmanifest", "sw.js", "icon-192.png", "icon-512.png"):
        assert f'"{name}"' in src, f"{name} is not served from the root"

    assert "_ROOT_PWA_FILES.get(filename)" in src, (
        "the root route no longer checks its allow-list before serving a file"
    )
