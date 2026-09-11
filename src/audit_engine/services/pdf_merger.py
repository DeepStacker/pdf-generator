"""Merge each branch folder's PDFs into one PDF per branch.

    root/                         Final_Output.zip
    ├── Branch A/                 ├── Branch A.pdf
    │   ├── file1.pdf      ->     ├── Branch B.pdf
    │   └── file2.pdf             └── Branch C.pdf
    ├── Branch B/ ...

One merged PDF per branch, flat in the zip, named after the branch. The
source PDFs do not travel with it.

The awkward part of this job is not merging, it is that the folders come from
whatever produced them. A branch that turns out to be empty, a file named
.pdf that is not one, an encrypted file, a stray PDF loose in the root, two
branches whose names differ only by a character the filesystem will not keep
-- all of these happen. None of them is a reason to fail the whole batch and
hand back nothing, so each is skipped and reported, and the run succeeds as
long as anything merged.
"""

from __future__ import annotations

import logging
import re
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

_NUMBER_RUN = re.compile(r"(\d+)")

# Characters a zip entry should not carry, whatever the branch folder is called.
_UNSAFE_IN_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class MergeError(Exception):
    """Raised only when nothing could be merged at all."""


def natural_key(name: str):
    """Sort file1, file2, file10 in that order -- not file1, file10, file2.

    Plain alphabetical order puts file10 before file2, which silently
    reorders the pages of a merged report. Digit runs are compared as
    numbers, everything else case-insensitively, so "Page 2" and "page 2"
    land together and leading zeros do not matter.
    """
    parts = _NUMBER_RUN.split(name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def safe_branch_name(name: str) -> str:
    """A branch name that survives being a filename inside a zip."""
    cleaned = _UNSAFE_IN_NAME.sub("_", name).strip().strip(".")
    return cleaned[:120] or "branch"


def find_branches(root: Path) -> tuple[dict[str, list[Path]], list[str]]:
    """Branch folder -> its PDFs in merge order, plus notes about what was skipped.

    Searched recursively inside each branch: a branch that arrives with its
    own subfolders is still one branch, and dropping those files silently
    would be worse than including them.
    """
    notes: list[str] = []
    branches: dict[str, list[Path]] = {}

    if not root.is_dir():
        raise MergeError(f"Not a folder: {root}")

    loose = sorted((p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"),
                   key=lambda p: natural_key(p.name))
    if loose:
        notes.append(
            f"{len(loose)} PDF(s) sat directly in the uploaded folder, outside any branch, and were skipped."
        )

    for child in sorted(root.iterdir(), key=lambda p: natural_key(p.name)):
        if not child.is_dir():
            continue
        pdfs = sorted((p for p in child.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"),
                      key=lambda p: natural_key(str(p.relative_to(child))))
        if not pdfs:
            notes.append(f"{child.name}: no PDFs, skipped.")
            continue
        branches[child.name] = pdfs

    if not branches:
        raise MergeError("No branch folder in there contained a PDF.")
    return branches, notes


def merge_branch(pdfs: list[Path], destination: Path) -> tuple[int, list[str]]:
    """Merge one branch. Returns the page count and notes about skipped files."""
    from pypdf import PdfReader, PdfWriter

    notes: list[str] = []
    writer = PdfWriter()
    pages = 0

    for pdf in pdfs:
        try:
            reader = PdfReader(str(pdf))
            if reader.is_encrypted:
                # Many "encrypted" PDFs in practice carry an empty owner
                # password and open fine; only give up if that fails.
                try:
                    reader.decrypt("")
                except Exception:
                    notes.append(f"{pdf.name}: password protected, skipped.")
                    continue
            for page in reader.pages:
                writer.add_page(page)
                pages += 1
        except Exception as exc:
            notes.append(f"{pdf.name}: unreadable ({type(exc).__name__}), skipped.")
            logger.warning("Skipping %s: %s", pdf.name, exc)

    if pages == 0:
        return 0, notes

    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "wb") as fh:
        writer.write(fh)
    return pages, notes


def merge_folder_to_zip(root, output_zip, on_progress=None) -> dict:
    """Merge every branch under `root` into one zip of per-branch PDFs."""
    root = Path(root)
    output_zip = Path(output_zip)

    def report(pct: float, message: str = "") -> None:
        if on_progress:
            on_progress(pct, message)

    branches, notes = find_branches(root)
    report(5, f"Found {len(branches)} branch folder(s).")

    work_dir = output_zip.parent / f".{output_zip.stem}_merging"
    work_dir.mkdir(parents=True, exist_ok=True)

    merged: list[tuple[str, Path, int, int]] = []
    used_names: set[str] = set()

    for index, (branch, pdfs) in enumerate(branches.items(), 1):
        name = safe_branch_name(branch)
        # Two branches can sanitise to the same name; neither should overwrite
        # the other inside the zip.
        candidate, suffix = name, 2
        while candidate.lower() in used_names:
            candidate = f"{name} ({suffix})"
            suffix += 1
        used_names.add(candidate.lower())

        destination = work_dir / f"{candidate}.pdf"
        report(5 + (index - 1) / len(branches) * 85, f"Merging {branch} ({len(pdfs)} file(s))")
        pages, branch_notes = merge_branch(pdfs, destination)
        notes.extend(f"{branch}: {n}" for n in branch_notes)

        if pages == 0:
            notes.append(f"{branch}: nothing readable to merge, skipped.")
            continue
        merged.append((candidate, destination, len(pdfs), pages))

    if not merged:
        raise MergeError("Nothing could be merged: no readable PDFs in any branch.")

    report(92, "Building the zip...")
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(output_zip), "w", zipfile.ZIP_DEFLATED) as zf:
        for name, path, _sources, _pages in merged:
            zf.write(str(path), f"{name}.pdf")

    for _name, path, _s, _p in merged:
        path.unlink(missing_ok=True)
    with __import__("contextlib").suppress(OSError):
        work_dir.rmdir()

    report(100, "Done.")
    return {
        "success": True,
        "zip_path": str(output_zip),
        "branches": [
            {"branch": name, "sources": sources, "pages": pages}
            for name, _p, sources, pages in merged
        ],
        "branch_count": len(merged),
        "total_sources": sum(s for _n, _p, s, _pg in merged),
        "total_pages": sum(p for _n, _p, _s, p in merged),
        "notes": notes,
    }
