"""Flatten a PDF: turn everything interactive into permanent page content.

A flattened report cannot be edited after the fact — form fields, checkboxes,
stamps and comments become part of the page, exactly as they looked. That is
what makes a signed-off audit document safe to circulate.

The work is done by qpdf through pikepdf, which ships as a wheel with qpdf
built in. That matters here: the original script shelled out to Ghostscript,
which would have to be installed on every machine and cannot be bundled, so it
could never work in the locked-down environments this app runs in.

File in, file out, no network — the same shape as the report validator, so the
desktop app and the web server can share it.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Annotations with no appearance of their own; flattening cannot bake them
# into the page, so they are simply dropped.
_DROP_SUBTYPES = {"/Link"}


class FlattenError(Exception):
    """The PDF could not be flattened, with a reason worth showing a user."""


def flatten_pdf(src_path, output_path=None, on_progress=None):
    """Flatten one PDF and return a summary of what changed.

    Args:
        src_path: the PDF to flatten. Never modified.
        output_path: where to write the result. Defaults to
            "<name>_flattened.pdf" beside the source.
        on_progress: optional callback(pct: int, message: str).

    Returns:
        A JSON-serializable dict: output_path, pages, fields_flattened,
        annotations_flattened, links_removed, and the two file sizes.

    Raises:
        FileNotFoundError: src_path does not exist.
        FlattenError: the file is not a readable PDF, is password protected,
            or could not be written.
    """
    def report(pct, message=""):
        if on_progress:
            on_progress(pct, message)

    src_path = Path(src_path)
    if not src_path.is_file():
        raise FileNotFoundError(f"File not found: {src_path}")

    out_path = Path(output_path) if output_path else src_path.with_name(
        f"{src_path.stem}_flattened.pdf"
    )
    if out_path.resolve() == src_path.resolve():
        raise FlattenError("The flattened file would overwrite the original.")

    try:
        import pikepdf
    except ImportError as exc:  # pragma: no cover - packaging guard
        raise FlattenError(
            "The PDF flattener is unavailable in this build (pikepdf is missing)."
        ) from exc

    report(5, "Opening PDF…")
    try:
        pdf = pikepdf.open(str(src_path))
    except pikepdf.PasswordError as exc:
        raise FlattenError("This PDF is password protected, so it cannot be flattened.") from exc
    except pikepdf.PdfError as exc:
        raise FlattenError(f"This file is not a readable PDF: {exc}") from exc

    with pdf:
        pages = len(pdf.pages)
        fields_before = _count_form_fields(pdf)
        annots_before = _count_annotations(pdf)

        report(35, f"Flattening {pages} page(s)…")
        try:
            # Bakes each annotation's appearance stream into the page content,
            # so a filled-in value stays visible after the field is gone.
            pdf.flatten_annotations()
        except Exception as exc:  # noqa: BLE001 - surface any qpdf failure as ours
            raise FlattenError(f"Could not flatten this PDF: {exc}") from exc

        report(70, "Removing leftover interactivity…")
        links_removed = _drop_bare_annotations(pdf)
        _drop_acroform(pdf)

        annots_after = _count_annotations(pdf)

        report(85, "Saving…")
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            pdf.save(str(out_path), linearize=True)
        except Exception as exc:  # noqa: BLE001
            raise FlattenError(f"Could not write the flattened PDF: {exc}") from exc

    report(100, "Complete")
    return {
        "output_path": str(out_path),
        "output_name": out_path.name,
        "source_name": src_path.name,
        "pages": pages,
        "fields_flattened": fields_before,
        "annotations_flattened": max(annots_before - annots_after - links_removed, 0),
        "links_removed": links_removed,
        "source_bytes": src_path.stat().st_size,
        "output_bytes": out_path.stat().st_size,
    }


def _count_form_fields(pdf):
    root = pdf.Root
    if "/AcroForm" not in root:
        return 0
    fields = root.AcroForm.get("/Fields")
    return len(fields) if fields is not None else 0


def _count_annotations(pdf):
    total = 0
    for page in pdf.pages:
        annots = page.get("/Annots")
        if annots is not None:
            total += len(annots)
    return total


def _drop_bare_annotations(pdf):
    """Remove annotations that have no appearance to bake in (links)."""
    removed = 0
    for page in pdf.pages:
        annots = page.get("/Annots")
        if annots is None:
            continue
        keep = []
        for annot in annots:
            subtype = str(annot.get("/Subtype", ""))
            if subtype in _DROP_SUBTYPES:
                removed += 1
                continue
            keep.append(annot)
        if len(keep) != len(annots):
            if keep:
                page["/Annots"] = pdf.make_indirect(keep)
            else:
                del page["/Annots"]
    return removed


def _drop_acroform(pdf):
    """Drop the interactive form definition once its fields are page content."""
    if "/AcroForm" in pdf.Root:
        del pdf.Root["/AcroForm"]




def secure_delete(path):
    """Overwrite a file with random bytes, then remove it.

    Uploaded PDFs are somebody's customer records; they are deleted the moment
    the flattened copy exists rather than lingering on the server's disk.
    """
    import os

    path = Path(path)
    if not path.is_file():
        return
    try:
        size = path.stat().st_size
        with open(path, "r+b") as handle:
            for _ in range(2):
                handle.seek(0)
                remaining = size
                while remaining > 0:
                    chunk = min(remaining, 65536)
                    handle.write(os.urandom(chunk))
                    remaining -= chunk
                handle.flush()
                os.fsync(handle.fileno())
        path.unlink()
    except OSError as exc:
        logger.warning("Could not securely delete %s: %s", path, exc)
        with __import__("contextlib").suppress(OSError):
            path.unlink()


def cleanup_dir(path):
    """Remove a temp directory and everything in it."""
    shutil.rmtree(str(path), ignore_errors=True)
