#!/usr/bin/env python3
import atexit
import contextlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from audit_engine_web.patches import apply_patches
apply_patches()

from audit_engine.app import create_app, shutdown_requested
from audit_engine.lib.bottle import route, request, response, static_file, run, hook, BaseRequest
BaseRequest.MEMFILE_MAX = 500 * 1024 * 1024  # 500 MB limit for file uploads
from audit_engine.utils.config import paths
from audit_engine._version import VERSION

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("audit_engine_web")

STATIC_DIR = Path(__file__).resolve().parent / "static"
UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="audit_engine_uploads_"))
OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="audit_engine_outputs_"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def _cleanup_temp():
    for d in (UPLOAD_DIR, OUTPUT_DIR):
        if d.exists():
            shutil.rmtree(str(d), ignore_errors=True)
            logger.info("Cleaned up: %s", d)
atexit.register(_cleanup_temp)

import time
import threading

# How long an abandoned upload or an undownloaded report may sit before the
# sweeper takes it. Anything still wanted is deleted explicitly long before
# this: inputs the moment their job ends, outputs the moment they are served.
IDLE_FILE_TTL = 120


def _start_temp_garbage_collector():
    """Delete what jobs leave behind, without deleting the workspace itself.

    This used to glob /tmp/audit_engine_* and remove any *directory* older
    than the TTL -- which matches UPLOAD_DIR and OUTPUT_DIR themselves, both
    created once at startup. Two quiet minutes and the server deleted the two
    directories it writes everything into. It was survivable between jobs
    because the run route recreates OUTPUT_DIR, but a job running longer than
    the TTL had its own inputs and half-written reports swept out from under
    it, since a deep write does not touch the root's mtime.

    So the roots are now off limits and only their contents age out, a run in
    progress is left alone entirely, and directories from *previous* server
    processes -- genuinely orphaned, nothing holds a handle on them -- are
    still removed.
    """
    def _job_running() -> bool:
        try:
            from audit_engine.tasks.workers import global_tracker
            return bool(global_tracker.is_running)
        except Exception:
            return False

    def gc_loop():
        while True:
            time.sleep(30)
            try:
                if _job_running():
                    continue
                now = time.time()

                # This process's workspace: age out the contents, keep the roots.
                for root in (UPLOAD_DIR, OUTPUT_DIR):
                    root.mkdir(parents=True, exist_ok=True)
                    for child in root.iterdir():
                        try:
                            if now - child.stat().st_mtime <= IDLE_FILE_TTL:
                                continue
                            if child.is_dir():
                                shutil.rmtree(str(child), ignore_errors=True)
                            else:
                                child.unlink()
                            logger.info("Zero-trace: swept idle %s", child.name)
                        except OSError:
                            pass

                # Workspaces left by earlier runs of this server.
                keep = {UPLOAD_DIR.resolve(), OUTPUT_DIR.resolve()}
                for stale in Path(tempfile.gettempdir()).glob("audit_engine_*"):
                    try:
                        if not stale.is_dir() or stale.resolve() in keep:
                            continue
                        if now - stale.stat().st_mtime > IDLE_FILE_TTL:
                            shutil.rmtree(str(stale), ignore_errors=True)
                            logger.info("Zero-trace: removed orphaned workspace %s", stale.name)
                    except OSError:
                        pass
            except Exception as e:
                logger.warning("Temp GC error: %s", e)

    t = threading.Thread(target=gc_loop, daemon=True)
    t.start()

_start_temp_garbage_collector()


# ---------------------------------------------------------------------------
# Zero-trace file handling
# ---------------------------------------------------------------------------
# These workbooks carry customer names, loan numbers and gold weights. Nothing
# is kept a moment longer than the request that needs it:
#
#   * every file the server touches lives under UPLOAD_DIR or OUTPUT_DIR, and
#     nothing outside those two can be listed, previewed or downloaded;
#   * starting a job wipes whatever the previous job left behind;
#   * a file is deleted once it has been handed to the browser;
#   * the sweeper above is the backstop for anything a crashed or abandoned
#     job left behind.
#
# The desktop build deliberately does none of this: there the output folder is
# one the user picked and the files are theirs to keep.

# Seconds to wait before unlinking a file that has just been served. Removing
# a file while it is still being sent is safe on POSIX — the open handle keeps
# reading the data — so this only has to outlast the response starting.
DOWNLOAD_DELETE_DELAY = 5.0


def _workspace_roots() -> tuple[Path, ...]:
    return (UPLOAD_DIR.resolve(), OUTPUT_DIR.resolve())


def _within_workspace(path: Path) -> bool:
    """True if path is inside a directory this server manages.

    Without this, "path" on the download and preview routes is any absolute
    path on the box — the history database and every other tenant's file
    included.
    """
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return any(resolved == root or root in resolved.parents for root in _workspace_roots())


def _reject_outside_workspace(path: Path) -> dict | None:
    if _within_workspace(path):
        return None
    logger.warning("Refused access to %s: outside the managed directories", path)
    response.status = 403
    return {"error": "Access denied"}


def _purge_workspace(keep_paths=()) -> int:
    """Delete everything under the managed directories except keep_paths.

    Used at the start of a job, so one customer's report is never sitting on
    disk while the next customer's is being produced.
    """
    keep = set()
    for raw in keep_paths:
        if raw:
            with contextlib.suppress(OSError):
                keep.add(Path(raw).resolve())

    removed = 0
    for root in (UPLOAD_DIR, OUTPUT_DIR):
        if not root.exists():
            continue
        for child in root.iterdir():
            child_resolved = child.resolve()
            # Keep the inputs for the job about to run, and the directory each
            # one sits in.
            if any(k == child_resolved or child_resolved in k.parents for k in keep):
                continue
            try:
                if child.is_dir():
                    shutil.rmtree(str(child), ignore_errors=True)
                else:
                    child.unlink()
                removed += 1
            except OSError as e:
                logger.warning("Could not clear %s: %s", child, e)
    return removed


def _reap_inputs_when_job_ends(paths) -> None:
    """Delete the uploaded workbooks as soon as the run stops needing them.

    They used to sit in the workspace until the idle sweeper noticed them,
    so a customer's source file outlived the job that consumed it by up to
    the TTL. Waiting on the tracker rather than a timer means the file goes
    the moment the run is over, however long the run took.
    """
    targets = [Path(p) for p in paths if p]
    if not targets:
        return

    def _wait_then_remove():
        try:
            from audit_engine.tasks.workers import global_tracker
            deadline = time.time() + 6 * 60 * 60
            # Give the worker thread a moment to raise the flag before watching it fall.
            time.sleep(2)
            while global_tracker.is_running and time.time() < deadline:
                time.sleep(2)
        except Exception:
            pass
        for target in targets:
            try:
                if target.is_dir():
                    shutil.rmtree(str(target), ignore_errors=True)
                elif target.exists():
                    target.unlink()
                else:
                    continue
                logger.info("Zero-trace: removed input after job")
            except OSError as e:
                logger.warning("Could not remove an input after the job: %s", e)
            # the per-upload folder goes too, so nothing is left naming the file
            parent = target.parent
            try:
                if parent.is_dir() and parent.resolve() != UPLOAD_DIR.resolve() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                pass

    threading.Thread(target=_wait_then_remove, daemon=True).start()


def _delete_after_download(*paths) -> None:
    """Remove files once the browser has them."""
    def _remove():
        for raw in paths:
            target = Path(raw)
            try:
                if target.is_dir():
                    shutil.rmtree(str(target), ignore_errors=True)
                elif target.exists():
                    target.unlink()
                else:
                    continue
                logger.info("Zero-trace: removed %s after download", target.name)
            except OSError as e:
                # Windows will not unlink a file that is still open. The purge
                # at the start of the next job catches it.
                logger.warning("Could not remove %s after download: %s", target, e)

    threading.Timer(DOWNLOAD_DELETE_DELAY, _remove).start()

app = create_app()

import audit_engine_web.report_routes as report_routes  # noqa: E402,F401 — registers /api/report/* on default_app

from audit_engine.database.legacy import set_config as _set_cfg
_set_cfg("out_path", str(OUTPUT_DIR))
_set_cfg("auto_open", "False")

INDEX_CACHE = None

@hook("after_request")
def _add_cors():
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"

@route("/", method=["GET", "HEAD"])
def serve_index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        response.status = 500
        return "<h1>500 - index.html not found</h1>"
    html = index_path.read_text(encoding="utf-8").replace("{{VERSION}}", VERSION)
    response.content_type = "text/html; charset=utf-8"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return html

@route("/favicon.ico")
def serve_favicon():
    return static_file("favicon.svg", root=str(STATIC_DIR))

@route("/static/<filename:path>")
def serve_static(filename):
    file_path = STATIC_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        response.status = 404
        return {"error": "File not found"}
    return static_file(str(file_path.name), root=str(file_path.parent))

# The PWA files have to answer from the site root: a service worker only
# controls the scope it is served from, and the manifest's icon paths are
# resolved against it. There is no catch-all for root paths here, so they are
# listed explicitly rather than opening one -- a catch-all rooted at the
# static directory is how directory traversal gets in.
_ROOT_PWA_FILES = {
    "manifest.webmanifest": "application/manifest+json",
    "sw.js": "application/javascript",
    "icon-192.png": "image/png",
    "icon-512.png": "image/png",
    "icon-maskable-192.png": "image/png",
    "icon-maskable-512.png": "image/png",
}


@route("/<filename>")
def serve_root_pwa_file(filename):
    mimetype = _ROOT_PWA_FILES.get(filename)
    if mimetype is None:
        response.status = 404
        return {"error": "Not found"}
    return static_file(filename, root=str(STATIC_DIR), mimetype=mimetype)


@route("/logo.png")
@route("/assets/logo.png")
def serve_logo():
    logo_path = STATIC_DIR / "assets" / "logo.png"
    if not logo_path.exists():
        logo_path = STATIC_DIR / "logo.png"
    return static_file(logo_path.name, root=str(logo_path.parent))

@route("/assets/<filename:path>")
def serve_assets(filename):
    file_path = STATIC_DIR / "assets" / filename
    if not file_path.exists() or not file_path.is_file():
        # Fallback to root STATIC_DIR if not in assets/
        file_path = STATIC_DIR / filename
        if not file_path.exists() or not file_path.is_file():
            response.status = 404
            return {"error": "Asset not found"}
    return static_file(str(file_path.name), root=str(file_path.parent))

@route("/api/upload", method=["OPTIONS", "POST"])
def handle_upload():
    if request.method == "OPTIONS":
        return {}
    upload = request.files.get("file")
    if not upload:
        return {"success": False, "error": "No file provided"}
    safe_name = "".join(c for c in upload.filename if c.isalnum() or c in "._- ")
    subdir = UPLOAD_DIR / str(uuid.uuid4())[:8]
    subdir.mkdir(parents=True, exist_ok=True)
    dest = subdir / safe_name
    upload.save(str(dest))
    # The name is the customer's, and this log outlives the file itself.
    logger.info("Upload received (%d bytes)", dest.stat().st_size if dest.exists() else 0)
    return {"success": True, "path": str(dest), "name": safe_name}

@route("/api/upload/multiple", method=["OPTIONS", "POST"])
def handle_upload_multiple():
    if request.method == "OPTIONS":
        return {}
    uploaded = request.files.getall("file")
    if not uploaded:
        return {"success": False, "error": "No files provided"}
    paths_list = []
    for upload in uploaded:
        safe_name = "".join(c for c in upload.filename if c.isalnum() or c in "._- ")
        subdir = UPLOAD_DIR / str(uuid.uuid4())[:8]
        subdir.mkdir(parents=True, exist_ok=True)
        dest = subdir / safe_name
        upload.save(str(dest))
        paths_list.append(str(dest))
    return {"success": True, "paths": paths_list}

@route("/api/download")
def handle_download():
    filepath = request.query.path
    if not filepath:
        response.status = 400
        return {"error": "No path provided"}
    abs_path = Path(filepath)
    denied = _reject_outside_workspace(abs_path)
    if denied:
        return denied
    if not abs_path.exists():
        response.status = 404
        return {"error": "File not found"}
    if abs_path.is_dir():
        zip_name = f"{abs_path.name}_{uuid.uuid4()}.zip"
        zip_path = OUTPUT_DIR / zip_name
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for f in abs_path.rglob("*"):
                zf.write(str(f), str(f.relative_to(abs_path)))
        # The folder has been handed over; neither it nor the zip stays behind.
        _delete_after_download(zip_path, abs_path)
        return static_file(zip_name, root=str(OUTPUT_DIR), download=zip_name)
    _delete_after_download(abs_path)
    ext = abs_path.suffix.lower()
    mimetypes = {'.pdf': 'application/pdf', '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xls': 'application/vnd.ms-excel', '.zip': 'application/zip', '.csv': 'text/csv', '.txt': 'text/plain'}
    response.content_type = mimetypes.get(ext, 'application/octet-stream')
    return static_file(str(abs_path.name), root=str(abs_path.parent), download=abs_path.name)

@route("/api/preview")
def handle_preview():
    filepath = request.query.path
    if not filepath:
        response.status = 400
        return {"error": "No path provided"}
    abs_path = Path(filepath)
    denied = _reject_outside_workspace(abs_path)
    if denied:
        return denied
    if not abs_path.exists():
        response.status = 404
        return {"error": "File not found"}
    ext = abs_path.suffix.lower()
    mimetypes = {
        '.pdf': 'application/pdf',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.csv': 'text/csv',
        '.txt': 'text/plain'
    }
    response.content_type = mimetypes.get(ext, 'application/octet-stream')
    response.headers["Content-Disposition"] = f"inline; filename=\"{abs_path.name}\""
    return static_file(str(abs_path.name), root=str(abs_path.parent))

@route("/api/preview/excel")
def handle_preview_excel():
    filepath = request.query.path
    requested_sheet = request.query.sheet
    max_rows_param = request.query.get('max_rows', '3000')
    try:
        max_rows_limit = int(max_rows_param)
    except ValueError:
        max_rows_limit = 3000

    if not filepath:
        return {"success": False, "error": "No path provided"}
    abs_path = Path(filepath)
    if not abs_path.exists():
        return {"success": False, "error": "File not found"}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(abs_path), read_only=True, data_only=True)
        sheet_names = wb.sheetnames
        sheet_name = requested_sheet if (requested_sheet and requested_sheet in sheet_names) else (sheet_names[0] if sheet_names else "Sheet1")
        ws = wb[sheet_name]
        rows = []
        for idx, row in enumerate(ws.iter_rows(values_only=True)):
            if idx >= max_rows_limit:
                break
            rows.append([str(c) if c is not None else "" for c in row])
        wb.close()
        headers = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []
        return {
            "success": True,
            "file_name": abs_path.name,
            "sheet_name": sheet_name,
            "sheet_names": sheet_names,
            "headers": headers,
            "rows": data_rows,
            "total_rows": len(data_rows),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@route("/api/consolidate/preparse", method="POST")
def handle_preparse():
    data = request.json or {}
    filepath = data.get("filepath")
    if not filepath:
        return {"success": False, "error": "No filepath provided"}
    from audit_engine.web.handlers import handle_preparse_file
    return handle_preparse_file(filepath)

@route("/api/download/zip", method="POST")
def handle_download_zip():
    data = request.json or {}
    paths_to_zip = data.get("paths", [])
    if not paths_to_zip:
        return {"success": False, "error": "No paths provided"}

    zip_name = f"audit_engine_output_{uuid.uuid4()}.zip"
    zip_path = OUTPUT_DIR / zip_name

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for item in paths_to_zip:
            p = Path(item)
            if p.exists() and p.is_file() and _within_workspace(p):
                zf.write(str(p), p.name)

    return {"success": True, "zip_path": str(zip_path)}

@route("/api/list_output")
def handle_list_output():
    dirpath = request.query.path
    if not dirpath:
        return {"success": False, "files": []}
    p = Path(dirpath)
    if not _within_workspace(p) or not p.exists():
        return {"success": False, "files": []}

    files = []
    if p.is_file():
        files.append({"name": p.name, "path": str(p), "size": p.stat().st_size})
    elif p.is_dir():
        for item in p.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "size": item.stat().st_size,
                    "rel_path": str(item.relative_to(p))
                })
    return {"success": True, "files": files}

@route("/api/history/<entry_id>/download/<filename:path>")
def handle_history_download(entry_id, filename):
    from audit_engine.database.legacy import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT output_path, full_path FROM history WHERE id = ?", (entry_id,))
    row = cursor.fetchone()
    if not row:
        response.status = 404
        return {"error": "History entry not found"}
    output_path = row[0]
    file_path = Path(output_path) / filename
    if not file_path.exists():
        file_path = Path(output_path)
        if not file_path.exists():
            response.status = 404
            return {"error": "File not found"}
    if file_path.is_dir():
        zip_name = f"history_{entry_id}_{uuid.uuid4()}.zip"
        zip_dest = OUTPUT_DIR / zip_name
        with zipfile.ZipFile(str(zip_dest), "w", zipfile.ZIP_DEFLATED) as zf:
            for f in file_path.rglob("*"):
                zf.write(str(f), str(f.relative_to(file_path)))
        return static_file(zip_name, root=str(OUTPUT_DIR), download=zip_name)
    return static_file(file_path.name, root=str(file_path.parent), download=file_path.name)

@route("/api/run", method="POST")
def web_run():
    """Start a job, after clearing out whatever the last one left behind."""
    from audit_engine.web.handlers import handle_run

    data = dict(request.json or {})

    raw_input = data.get("filepath")
    inputs = raw_input if isinstance(raw_input, list) else ([raw_input] if raw_input else [])

    # Outputs are pinned inside the managed directory whatever the client asks
    # for, so the purge below and the sweeper can always reach them — and so a
    # crafted request cannot write a report into an arbitrary path.
    #
    # Recreated first: the idle sweeper deletes this directory once a couple of
    # minutes pass with nothing written to it, and handle_run rejects an
    # out_path that does not exist. Without this, the first job after a quiet
    # spell failed with "Output directory invalid."
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data["out_path"] = str(OUTPUT_DIR)

    cleared = _purge_workspace(keep_paths=inputs)
    if cleared:
        logger.info("Zero-trace: cleared %d item(s) left by the previous job", cleared)

    result = handle_run(data)
    if isinstance(result, dict) and result.get("success"):
        _reap_inputs_when_job_ends(inputs)
    return result


@route("/api/update/check")
def web_update_check():
    return {"update_ready": False, "current": VERSION, "error": "Auto-update not available in web mode"}

@route("/api/update/install", method="POST")
def web_update_install():
    return {"success": False, "error": "Auto-update not available in web mode"}

@route("/api/update/progress")
def web_update_progress():
    return {"pct": 0, "is_downloading": False, "success": False, "error": "Auto-update not available in web mode"}

@route("/api/update/apply", method="POST")
def web_update_apply():
    return {"success": False, "error": "Auto-update not available in web mode"}

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Audit Engine Elite - Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)), help="Port to bind to (default: 8080, or $PORT env)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Audit Engine Elite Web v%s", VERSION)
    logger.info("Upload directory: %s", UPLOAD_DIR)
    logger.info("Output directory: %s", OUTPUT_DIR)
    logger.info("Database: %s", paths.db)
    logger.info("Listening on http://%s:%d", args.host, args.port)
    logger.info("=" * 60)

    try:
        run(app=app, host=args.host, port=args.port, debug=args.debug, quiet=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == "__main__":
    main()
