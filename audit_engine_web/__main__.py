#!/usr/bin/env python3
import atexit
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

def _start_temp_garbage_collector():
    def gc_loop():
        while True:
            time.sleep(900)  # Check every 15 minutes
            try:
                now = time.time()
                temp_root = Path(tempfile.gettempdir())
                for p in temp_root.glob("audit_engine_*"):
                    if p.is_dir() and p not in (UPLOAD_DIR, OUTPUT_DIR):
                        try:
                            if now - p.stat().st_mtime > 3600:
                                shutil.rmtree(str(p), ignore_errors=True)
                                logger.info("GC pruned stale temp dir: %s", p.name)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning("Temp GC error: %s", e)

    t = threading.Thread(target=gc_loop, daemon=True)
    t.start()

_start_temp_garbage_collector()

app = create_app()

from audit_engine.database.legacy import set_config as _set_cfg
_set_cfg("out_path", str(OUTPUT_DIR))
_set_cfg("auto_open", "False")

INDEX_CACHE = None

@hook("after_request")
def _add_cors():
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    if request.path.startswith("/static/") and request.path.endswith((".png", ".svg", ".ico")):
        response.headers["Cache-Control"] = "public, max-age=86400"
    elif request.path.startswith("/static/") and request.path.endswith((".css", ".js")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"

@route("/", method=["GET", "HEAD"])
def serve_index():
    global INDEX_CACHE
    if INDEX_CACHE is None:
        index_path = STATIC_DIR / "index.html"
        if not index_path.exists():
            response.status = 500
            return "<h1>500 - index.html not found</h1>"
        INDEX_CACHE = index_path.read_text(encoding="utf-8")
    html = INDEX_CACHE.replace("{{VERSION}}", VERSION)
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

@route("/assets/<filename:path>")
def serve_assets(filename):
    file_path = STATIC_DIR / "assets" / filename
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
    logger.info("Uploaded: %s -> %s", upload.filename, dest)
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
    if not abs_path.exists():
        response.status = 404
        return {"error": "File not found"}
    if abs_path.is_dir():
        zip_name = f"{abs_path.name}_{uuid.uuid4()}.zip"
        zip_path = OUTPUT_DIR / zip_name
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for f in abs_path.rglob("*"):
                zf.write(str(f), str(f.relative_to(abs_path)))
        return static_file(zip_name, root=str(OUTPUT_DIR), download=zip_name)
    ext = abs_path.suffix.lower()
    mimetypes = {'.pdf': 'application/pdf', '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xls': 'application/vnd.ms-excel', '.zip': 'application/zip', '.csv': 'text/csv', '.txt': 'text/plain'}
    response.content_type = mimetypes.get(ext, 'application/octet-stream')
    return static_file(str(abs_path.name), root=str(abs_path.parent), download=abs_path.name)

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
            if p.exists() and p.is_file():
                zf.write(str(p), p.name)

    return {"success": True, "zip_path": str(zip_path)}

@route("/api/list_output")
def handle_list_output():
    dirpath = request.query.path
    if not dirpath:
        return {"success": False, "files": []}
    p = Path(dirpath)
    if not p.exists():
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
