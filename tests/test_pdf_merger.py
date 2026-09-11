"""Merging each branch folder's PDFs into one PDF per branch.

The merging itself is the easy half. The folders arrive from whatever
produced them, so the tests that matter are the ones about mess: a branch
that is empty, a file called .pdf that is not one, a branch name the
filesystem will not keep, PDFs loose in the root. None of those should cost
the operator the whole batch.
"""

import io
import zipfile
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from audit_engine.services.pdf_merger import (
    MergeError,
    merge_folder_to_zip,
    natural_key,
    safe_branch_name,
)


def _pdf(path: Path, pages: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as fh:
        writer.write(fh)
    return path


def _pages_of(zip_path: Path, entry: str) -> int:
    with zipfile.ZipFile(zip_path) as zf:
        return len(PdfReader(io.BytesIO(zf.read(entry))).pages)


def test_the_shape_from_the_specification(tmp_path):
    """Branch folders in, one flat PDF per branch out, sources not included."""
    root = tmp_path / "Uploaded Folder"
    for branch, count in (("Branch A", 3), ("Branch B", 3), ("Branch C", 2)):
        for i in range(1, count + 1):
            _pdf(root / branch / f"file{i}.pdf")

    out = tmp_path / "Final_Output.zip"
    result = merge_folder_to_zip(root, out)

    with zipfile.ZipFile(out) as zf:
        assert sorted(zf.namelist()) == ["Branch A.pdf", "Branch B.pdf", "Branch C.pdf"]
    assert result["branch_count"] == 3
    assert result["total_sources"] == 8
    assert _pages_of(out, "Branch A.pdf") == 3


def test_pages_follow_natural_order_not_alphabetical():
    """file10 after file2, or a merged report comes out shuffled."""
    assert sorted(["file10.pdf", "file2.pdf", "file1.pdf"], key=natural_key) == [
        "file1.pdf", "file2.pdf", "file10.pdf",
    ]
    # leading zeros and case must not change the grouping either
    assert sorted(["B2.pdf", "b10.pdf", "B01.pdf"], key=natural_key) == [
        "B01.pdf", "B2.pdf", "b10.pdf",
    ]


def test_one_unreadable_file_does_not_cost_the_branch(tmp_path):
    """The whole point of reporting rather than raising."""
    root = tmp_path / "root"
    _pdf(root / "Broken" / "good.pdf", pages=2)
    (root / "Broken" / "corrupt.pdf").write_bytes(b"not a pdf at all")

    result = merge_folder_to_zip(root, tmp_path / "out.zip")

    assert result["branch_count"] == 1
    assert _pages_of(tmp_path / "out.zip", "Broken.pdf") == 2
    assert any("corrupt.pdf" in note for note in result["notes"]), result["notes"]


def test_empty_branches_and_loose_files_are_reported_not_silent(tmp_path):
    root = tmp_path / "root"
    _pdf(root / "Real" / "a.pdf")
    (root / "Empty").mkdir(parents=True)
    _pdf(root / "loose.pdf")

    result = merge_folder_to_zip(root, tmp_path / "out.zip")

    assert result["branch_count"] == 1
    assert any("Empty" in n for n in result["notes"])
    assert any("outside any branch" in n for n in result["notes"])


def test_a_branch_keeps_its_own_subfolders(tmp_path):
    """A branch that arrives with subfolders is still one branch."""
    root = tmp_path / "root"
    _pdf(root / "Branch" / "top.pdf")
    _pdf(root / "Branch" / "extra" / "deeper.pdf")

    merge_folder_to_zip(root, tmp_path / "out.zip")
    assert _pages_of(tmp_path / "out.zip", "Branch.pdf") == 2


def test_branch_names_survive_becoming_filenames(tmp_path):
    assert safe_branch_name("Bad:Name") == "Bad_Name"
    assert safe_branch_name("a/b\\c") == "a_b_c"
    assert safe_branch_name("   ") == "branch"
    assert "/" not in safe_branch_name("../../etc")

    # two branches that clean to the same name must not overwrite each other
    root = tmp_path / "root"
    _pdf(root / "Team:A" / "x.pdf")
    _pdf(root / "Team/A".replace("/", "|") / "y.pdf")

    merge_folder_to_zip(root, tmp_path / "out.zip")
    with zipfile.ZipFile(tmp_path / "out.zip") as zf:
        names = zf.namelist()
    assert len(names) == len(set(names)) == 2, names


def test_nothing_mergeable_is_an_error_not_an_empty_zip(tmp_path):
    """An empty zip looks like success and is not."""
    root = tmp_path / "root"
    (root / "Branch").mkdir(parents=True)

    with pytest.raises(MergeError):
        merge_folder_to_zip(root, tmp_path / "out.zip")

    root2 = tmp_path / "root2"
    (root2 / "Branch").mkdir(parents=True)
    (root2 / "Branch" / "broken.pdf").write_bytes(b"nope")
    with pytest.raises(MergeError):
        merge_folder_to_zip(root2, tmp_path / "out2.zip")


def test_the_sources_do_not_travel_with_the_result(tmp_path):
    """"The individual source PDFs should not be included separately.\""""
    root = tmp_path / "root"
    _pdf(root / "Branch A" / "file1.pdf")
    _pdf(root / "Branch A" / "file2.pdf")

    merge_folder_to_zip(root, tmp_path / "out.zip")
    with zipfile.ZipFile(tmp_path / "out.zip") as zf:
        assert zf.namelist() == ["Branch A.pdf"]


class TestDesktopHandlers:
    """The desktop path: a folder on disk in, a zip beside it out.

    Nothing is uploaded here, so the thing worth pinning is where the zip
    lands. Writing it *inside* the folder that was picked would make one
    run's output part of the next run's input, and running twice would
    silently overwrite the first result.
    """

    @pytest.fixture(autouse=True)
    def _reset(self):
        from audit_engine.web import merge_handlers as mh
        mh.merge_tracker.__init__()
        yield
        mh.merge_tracker.__init__()

    @pytest.fixture
    def branches(self, tmp_path):
        root = tmp_path / "Uploaded Folder"
        _pdf(root / "Branch A" / "file1.pdf", pages=2)
        _pdf(root / "Branch A" / "file2.pdf")
        _pdf(root / "Branch B" / "file1.pdf")
        return root

    def _wait(self, timeout=20.0):
        import time

        from audit_engine.web import merge_handlers as mh
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not mh.merge_tracker.is_running:
                return True
            time.sleep(0.05)
        return False

    def test_rejects_bad_input(self, tmp_path):
        from audit_engine.web import merge_handlers as mh
        assert mh.handle_merge_run({})["success"] is False
        assert mh.handle_merge_run({"folder": str(tmp_path / "ghost")})["success"] is False

        a_file = tmp_path / "not_a_folder.pdf"
        _pdf(a_file)
        assert mh.handle_merge_run({"folder": str(a_file)})["success"] is False

    def test_full_run_cycle(self, branches):
        from audit_engine.web import merge_handlers as mh
        assert mh.handle_merge_run({"folder": str(branches)})["success"] is True
        assert self._wait(), "merge did not finish"

        state = mh.handle_merge_progress()
        assert state["error"] is None
        assert state["pct"] == 100
        summary = state["summary"]
        assert summary["branch_count"] == 2
        assert summary["total_pages"] == 4
        zip_path = Path(summary["zip_path"])
        assert zip_path.is_file()
        with zipfile.ZipFile(zip_path) as zf:
            assert sorted(zf.namelist()) == ["Branch A.pdf", "Branch B.pdf"]
        assert any(log["level"] == "OK" for log in state["logs"])

    def test_the_zip_lands_beside_the_folder_not_inside_it(self, branches):
        from audit_engine.web import merge_handlers as mh
        mh.handle_merge_run({"folder": str(branches)})
        assert self._wait()

        zip_path = Path(mh.handle_merge_progress()["summary"]["zip_path"])
        assert zip_path.parent == branches.parent
        assert list(branches.rglob("*.zip")) == [], "the zip was written into the input folder"
        # and the merger's scratch directory did not survive either
        assert [p.name for p in branches.parent.iterdir() if p.is_dir()] == [branches.name]

    def test_a_second_run_does_not_overwrite_the_first(self, branches):
        from audit_engine.web import merge_handlers as mh
        mh.handle_merge_run({"folder": str(branches)})
        assert self._wait()
        first = Path(mh.handle_merge_progress()["summary"]["zip_path"])

        mh.merge_tracker.__init__()
        mh.handle_merge_run({"folder": str(branches)})
        assert self._wait()
        second = Path(mh.handle_merge_progress()["summary"]["zip_path"])

        assert first.is_file() and second.is_file()
        assert first != second

    def test_a_folder_with_nothing_to_merge_surfaces_as_an_error(self, tmp_path):
        from audit_engine.web import merge_handlers as mh
        empty = tmp_path / "Empty Folder"
        (empty / "Branch A").mkdir(parents=True)
        mh.handle_merge_run({"folder": str(empty)})
        assert self._wait()

        state = mh.handle_merge_progress()
        assert state["error"]
        assert state["is_running"] is False, "tracker must not stay stuck"

    def test_second_run_refused_while_active(self, branches):
        from audit_engine.web import merge_handlers as mh
        mh.merge_tracker.is_running = True
        try:
            assert mh.handle_merge_run({"folder": str(branches)})["success"] is False
        finally:
            mh.merge_tracker.is_running = False

    def test_open_rejects_a_missing_path(self):
        from audit_engine.web import merge_handlers as mh
        assert mh.handle_merge_open({})["success"] is False
        assert mh.handle_merge_open({"path": "/definitely/not/here.zip"})["success"] is False


class TestZeroSocketBridge:
    """The desktop calls these routes through the bridge, never a socket.

    A route that works when called directly and is missing from the app is
    indistinguishable from the outside until someone clicks it.
    """

    def test_end_to_end_over_the_bridge(self, tmp_path):
        import json
        import time

        from audit_engine.app import create_app
        from audit_engine.web import merge_handlers as mh
        from audit_engine.web.bridge import WebViewBridge

        root = tmp_path / "Branches"
        _pdf(root / "Branch A" / "file1.pdf")
        _pdf(root / "Branch B" / "file1.pdf", pages=3)

        create_app()
        bridge = WebViewBridge()
        mh.merge_tracker.__init__()

        started = json.loads(bridge.fetch_proxy(
            "POST", "/api/merge/run", json.dumps({"folder": str(root)})
        ))
        assert started["success"] is True

        deadline = time.time() + 20
        payload = None
        while time.time() < deadline:
            payload = json.loads(bridge.fetch_proxy("GET", "/api/merge/progress", ""))
            if not payload["is_running"]:
                break
            time.sleep(0.05)

        assert payload and payload["error"] is None
        assert payload["summary"]["total_pages"] == 4
        assert Path(payload["summary"]["zip_path"]).is_file()
        mh.merge_tracker.__init__()


def test_web_mode_disables_the_desktop_merge_handlers():
    """Over HTTP these would pop a dialog on the server and read its disk.

    routes.py imports the handlers by name at import time, so patching only
    the defining module leaves the live route calling the real thing —
    the trap that once left web mode still writing history. Assert on the
    binding the route actually holds.
    """
    from audit_engine_web.patches import apply_patches

    apply_patches()

    import audit_engine.web.merge_handlers as merge_mod
    import audit_engine.web.routes as routes_mod

    for mod in (merge_mod, routes_mod):
        assert mod.handle_merge_run({"folder": "/etc"})["success"] is False
        assert mod.handle_merge_browse()["path"] == ""
        assert mod.handle_merge_open({"path": "/etc/passwd"})["success"] is False


class TestBrowserUploadShape:
    """What the browser sends is a shape, and the shape is client-supplied.

    Every PDF arrives with the path it had inside the picked folder, which
    decides the branch it merges into -- so the path cannot be dropped, and
    cannot be trusted either.
    """

    class _Upload:
        def __init__(self, raw_filename, data=b"%PDF-1.4\n"):
            self.raw_filename = raw_filename
            self.filename = raw_filename
            self.file = io.BytesIO(data)

    def _rebuild(self, pairs, root):
        from audit_engine_web.report_routes import _rebuild_upload_tree
        uploads = [self._Upload(Path(p).name) for p, _ in pairs]
        return _rebuild_upload_tree(uploads, [p for p, _ in pairs], root)

    def test_the_root_folder_is_dropped_and_branches_are_kept(self, tmp_path):
        root = tmp_path / "rebuilt"
        written = self._rebuild(
            [("Uploaded Folder/Branch A/file1.pdf", None),
             ("Uploaded Folder/Branch A/scans/file2.pdf", None),
             ("Uploaded Folder/Branch B/file1.pdf", None)],
            root,
        )
        assert written == 3
        assert (root / "Branch A" / "file1.pdf").is_file()
        assert (root / "Branch A" / "scans" / "file2.pdf").is_file()
        assert (root / "Branch B" / "file1.pdf").is_file()

    def test_a_path_cannot_climb_out_of_the_workspace(self, tmp_path):
        root = tmp_path / "rebuilt"
        outside = tmp_path / "pwned"
        self._rebuild([("x/../../../../../../tmp/pwned/evil.pdf", None)], root)
        assert not outside.exists()
        assert not any(p.name == "evil.pdf" for p in tmp_path.rglob("*") if root not in p.parents and p != root)

    def test_only_pdfs_are_written(self, tmp_path):
        root = tmp_path / "rebuilt"
        written = self._rebuild(
            [("Folder/Branch A/notes.txt", None), ("Folder/Branch A/file1.PDF", None)],
            root,
        )
        assert written == 1
        assert [p.name for p in root.rglob("*") if p.is_file()] == ["file1.PDF"]


class TestNotesHeader:
    """The notes say which branches did not make it, so they have to arrive.

    They travel in a response header, which has a size limit. Truncating the
    JSON itself produced something the browser could not parse at all -- the
    operator would have been told nothing rather than told most of it.
    """

    def test_a_short_list_travels_whole(self):
        from audit_engine_web.report_routes import _notes_that_fit
        notes = ["Branch D: no PDFs, skipped."] * 3
        assert _notes_that_fit(notes) == notes

    def test_a_long_list_stays_parseable_and_says_what_was_dropped(self):
        import json as _json

        from audit_engine_web.report_routes import _notes_that_fit
        notes = [f"Branch {i}: file_{i}.pdf: unreadable (PdfStreamError), skipped." for i in range(400)]
        kept = _notes_that_fit(notes)

        blob = _json.dumps(kept)
        assert len(blob) <= 3800
        assert _json.loads(blob) == kept, "the header must survive JSON.parse in the browser"
        assert kept[-1].startswith("...and ")
        shown = len(kept) - 1
        assert shown + int(kept[-1].split()[1]) == len(notes), "the count must account for every note"

    def test_no_notes_is_an_empty_list_not_a_marker(self):
        from audit_engine_web.report_routes import _notes_that_fit
        assert _notes_that_fit([]) == []
