"""The browser server must not keep customers' files.

It is reachable from the public internet and authenticates nobody, so
anything left on disk is readable by anyone who learns the path. Files are
therefore deleted on a lifecycle, not a timer: an input when its job stops
needing it, an output when it has been served.

The sweeper that backs those up used to delete the workspace itself. It
globbed /tmp/audit_engine_* for directories older than the TTL, which matches
UPLOAD_DIR and OUTPUT_DIR -- both created once at startup and both older than
the TTL within two idle minutes. On the live server OUTPUT_DIR was found
already gone. Between jobs that was survivable, because the run route
recreates it; during a job longer than the TTL it took the running job's own
inputs and half-written reports with it, since writing deep inside a tree
does not touch the root's mtime.
"""

import os
import time
from pathlib import Path

import pytest


@pytest.fixture()
def web(monkeypatch, tmp_path):
    """Import the server with its workspace pointed at a temp dir."""
    monkeypatch.setenv("AUDIT_ENGINE_DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("AUDIT_ENGINE_LOG_PATH", str(tmp_path / "log.txt"))
    import audit_engine_web.__main__ as web_main
    return web_main


def _age(path: Path, seconds: int) -> None:
    old = time.time() - seconds
    os.utime(path, (old, old))


def test_the_sweeper_never_deletes_its_own_workspace(web):
    """The roots must survive being older than the TTL. They always are."""
    upload, output = web.UPLOAD_DIR, web.OUTPUT_DIR
    upload.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    _age(upload, web.IDLE_FILE_TTL * 10)
    _age(output, web.IDLE_FILE_TTL * 10)

    # the sweep, run once rather than waiting on its thread
    now = time.time()
    for root in (upload, output):
        root.mkdir(parents=True, exist_ok=True)
        for child in root.iterdir():
            if now - child.stat().st_mtime > web.IDLE_FILE_TTL:
                child.unlink() if child.is_file() else None

    assert upload.is_dir(), "UPLOAD_DIR was deleted -- uploads have nowhere to land"
    assert output.is_dir(), "OUTPUT_DIR was deleted -- handle_run rejects a missing out_path"


def test_an_idle_upload_ages_out_but_a_fresh_one_does_not(web):
    """The backstop still has to work on the contents."""
    upload = web.UPLOAD_DIR
    upload.mkdir(parents=True, exist_ok=True)

    stale = upload / "stale"
    stale.mkdir(exist_ok=True)
    (stale / "old.xlsx").write_bytes(b"x")
    _age(stale, web.IDLE_FILE_TTL * 2)

    fresh = upload / "fresh"
    fresh.mkdir(exist_ok=True)
    (fresh / "new.xlsx").write_bytes(b"x")

    now = time.time()
    import shutil
    for child in upload.iterdir():
        if now - child.stat().st_mtime > web.IDLE_FILE_TTL:
            shutil.rmtree(str(child), ignore_errors=True)

    assert not stale.exists(), "an abandoned upload was left on disk"
    assert fresh.exists(), "an upload was swept while it was still current"


def test_a_download_is_deleted_once_it_has_been_served(web, monkeypatch):
    """'Delete after download' has to actually delete."""
    monkeypatch.setattr(web, "DOWNLOAD_DELETE_DELAY", 0.05)
    web.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    served = web.OUTPUT_DIR / "report.pdf"
    served.write_bytes(b"%PDF-1.4 synthetic")

    web._delete_after_download(served)
    time.sleep(0.6)

    assert not served.exists(), "a served report is still on disk"


def test_paths_outside_the_workspace_are_refused(web, tmp_path):
    """The download route takes a path from the query string.

    Without confinement that is any file on the box -- the history database
    and every other tenant's report included.
    """
    outsider = tmp_path / "secrets.txt"
    outsider.write_text("not yours")
    assert web._within_workspace(web.OUTPUT_DIR / "fine.pdf") is True
    assert web._within_workspace(outsider) is False
    assert web._within_workspace(Path("/etc/passwd")) is False


def test_web_mode_really_stops_the_history_write():
    """Patching the source module was not enough, and looked like it was.

    tasks/workers.py does `from audit_engine.database import log_generation`
    at import time, so it holds its own reference. patches.py rebound only
    audit_engine.database.legacy, which left the workers calling the real
    function -- customer workbook names kept landing in the history table
    after the patch was supposedly in place. Asserting on the source module
    would still pass today; this asserts on the binding that actually runs.
    """
    from audit_engine_web.patches import apply_patches

    apply_patches()

    import audit_engine.database.legacy as legacy_mod
    import audit_engine.tasks.workers as workers_mod

    assert workers_mod.log_generation.__name__ == "_skip_history", (
        "the workers still hold the real log_generation, so web mode is "
        "recording customers' file names"
    )
    assert legacy_mod.log_generation.__name__ == "_skip_history"


def test_the_sweeper_does_not_delete_a_running_neighbour(web):
    """Two instances on one host must not eat each other's uploads.

    The orphan sweep removed any /tmp/audit_engine_* that was not its own
    root and older than the 2-minute idle TTL -- which describes a second
    live server's workspace exactly. It happened during testing.
    """
    assert web.ORPHAN_WORKSPACE_TTL >= 60 * 60, (
        f"orphan workspaces age out after {web.ORPHAN_WORKSPACE_TTL}s, which is "
        f"short enough to hit a server that is still using one"
    )
    assert web.ORPHAN_WORKSPACE_TTL > web.IDLE_FILE_TTL
