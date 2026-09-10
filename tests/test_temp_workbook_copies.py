"""A mapped run copies the whole workbook; the copy must not outlive the run.

preprocess_mapped_excel writes a full copy of the customer's spreadsheet to
~/.temp_audit_engine/mapped_<name>. Nothing sweeps that directory: the web
server's collector only walks /tmp, and its workspace purge only covers the
upload and output directories. The worker that used it was the only thing
that ever deleted it.

Which it did on the success path, inside the try. A run that raised -- an
unreadable sheet, a corrupt file, the everyday reasons a run fails -- left
the copy on disk for good. The Arvog worker never called it at all, so an
Arvog mapped run always did.

Both front ends drive these same workers, so this applies to the desktop app
and the browser server alike.
"""

import os

import pytest

from audit_engine.tasks import workers


@pytest.fixture()
def temp_mapped(tmp_path, monkeypatch):
    """A file shaped like one preprocess_mapped_excel would have written."""
    home = tmp_path / "home"
    tmp_dir = home / ".temp_audit_engine"
    tmp_dir.mkdir(parents=True)
    copy = tmp_dir / "mapped_customer_book.xlsx"
    copy.write_bytes(b"stand-in for the customer's workbook")
    return copy


def test_the_copy_is_removed_when_a_run_fails(temp_mapped, monkeypatch):
    """The failure path is exactly when a copy used to be left behind."""
    monkeypatch.setattr(workers, "log_generation", lambda *a, **k: None)
    monkeypatch.setattr(workers, "trigger_notification", lambda *a, **k: None)

    # read_excel raising is how a bad workbook surfaces
    def _boom(*_a, **_k):
        raise ValueError("No valid sheet found.")
    monkeypatch.setattr(workers.pdf_logic, "read_excel", _boom)

    workers.cancel_event.clear()
    workers.worker_idfc_thread([str(temp_mapped)], str(temp_mapped.parent), "POA", "FOLDER", False, "{branch}_{type}")

    assert not temp_mapped.exists(), "a failed run left the customer's workbook copy on disk"


@pytest.mark.parametrize("worker,args", [
    ("worker_idfc_thread", ("POA", "FOLDER", False, "{branch}_{type}")),
    ("worker_arvog_thread", (False, "BOTH", "FOLDER")),
])
def test_every_worker_removes_the_copy(temp_mapped, monkeypatch, worker, args):
    """Arvog never cleaned up; the others only did when they succeeded."""
    monkeypatch.setattr(workers, "log_generation", lambda *a, **k: None)
    monkeypatch.setattr(workers, "trigger_notification", lambda *a, **k: None)

    def _boom(*_a, **_k):
        raise ValueError("unreadable")
    monkeypatch.setattr(workers.pdf_logic, "read_excel", _boom, raising=False)

    workers.cancel_event.clear()
    getattr(workers, worker)([str(temp_mapped)], str(temp_mapped.parent), *args)

    assert not temp_mapped.exists(), f"{worker} left the copy behind"


def test_only_the_engine_s_own_copies_are_deleted(tmp_path):
    """The guard must not reach a file the user chose themselves.

    The input to a normal run is the customer's own spreadsheet, sitting
    wherever they keep it. Deleting that would destroy their data.
    """
    real = tmp_path / "quarterly_audit.xlsx"
    real.write_bytes(b"the user's own file")

    workers._cleanup_temp_mapped([str(real)])

    assert real.exists(), "cleanup deleted a file the engine did not create"
