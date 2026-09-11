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
