#!/usr/bin/env python3
import atexit
import contextlib
import json
import logging
import os
import re
import shutil
import signal
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from audit_engine_web import auth
from audit_engine_web.patches import apply_patches
apply_patches()

from audit_engine.app import create_app, shutdown_requested
from audit_engine.lib.bottle import (
    route, request, response, static_file, run, hook, BaseRequest, HTTPResponse,
)
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


def _cleanup_on_signal(signum, _frame):
    """Clear the workspace on SIGTERM as well as on a clean exit.

    atexit does not run when the process is signalled, and SIGTERM is exactly
    how a container is stopped -- so every `podman compose down` or redeploy
    left a workspace of customer uploads behind for the sweeper to find later.
    Re-raising with the default handler afterwards keeps the exit status
    honest for whatever is supervising.
    """
    _cleanup_temp()
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


for _sig in (signal.SIGTERM, signal.SIGINT):
    try:
        signal.signal(_sig, _cleanup_on_signal)
    except (ValueError, OSError):
        # Not the main thread, or a platform without it; atexit still covers
        # the clean-exit path.
        pass

import time
import threading

# How long an abandoned upload or an undownloaded report may sit before the
# sweeper takes it. Anything still wanted is deleted explicitly long before
# this: inputs the moment their job ends, outputs the moment they are served.
IDLE_FILE_TTL = 120

# How long a workspace belonging to no running instance may sit. Only ever
# applied to directories this process does not own -- see the sweeper.
ORPHAN_WORKSPACE_TTL = 24 * 60 * 60


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
                #
                # The age bar is deliberately much higher than IDLE_FILE_TTL.
                # A second instance's workspace looks identical to an
                # abandoned one, and at the TTL this deleted the in-flight
                # uploads of a server running alongside it -- seen for real
                # when two instances were up at once. A day old means nothing
                # is still using it, whereas two minutes old means very
                # little.
                keep = {UPLOAD_DIR.resolve(), OUTPUT_DIR.resolve()}
                for stale in Path(tempfile.gettempdir()).glob("audit_engine_*"):
                    try:
                        if not stale.is_dir() or stale.resolve() in keep:
                            continue
                        if now - stale.stat().st_mtime > ORPHAN_WORKSPACE_TTL:
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


def _reap_inputs_when_job_ends(paths, still_running=None) -> None:
    """Delete the uploaded workbooks as soon as the run stops needing them.

    They used to sit in the workspace until the idle sweeper noticed them,
    so a customer's source file outlived the job that consumed it by up to
    the TTL. Waiting on the tracker rather than a timer means the file goes
    the moment the run is over, however long the run took.

    `still_running` says which run to wait on. Bank jobs report through
    global_tracker and consolidation through consolidation_tracker, so
    defaulting to the former and passing the latter is the difference
    between deleting a file when its job ends and deleting it while another
    job is still reading it.
    """
    targets = [Path(p) for p in paths if p]
    if not targets:
        return

    def _wait_then_remove():
        try:
            check = still_running
            if check is None:
                from audit_engine.tasks.workers import global_tracker
                def check():
                    return global_tracker.is_running
            deadline = time.time() + 6 * 60 * 60
            # Give the worker thread a moment to raise the flag before watching it fall.
            time.sleep(2)
            while check() and time.time() < deadline:
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
def _security_headers():
    # No Access-Control-Allow-Origin. The browser app is served from this same
    # origin and never makes a cross-origin call, so the previous blanket "*"
    # bought nothing and advertised every endpoint to any page on the web.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Served over TLS by the Tailscale proxy; this stops a downgrade on a
    # hostname a browser has already seen once.
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    # The app loads only its own bundle and an inline style block; nothing is
    # fetched from anywhere else, so everything but self can be refused.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    )

# ---------------------------------------------------------------------------
# The password gate.
#
# Everything this server exposes acts on customers' audit workbooks, and it
# answers the public internet, so the default is "no". Only the login form
# itself, and the handful of files a browser needs to render it, are open.
#
# The desktop app never reaches any of this: it talks to the same handlers
# over an in-process bridge and opens no socket.
# ---------------------------------------------------------------------------

# The login page must be able to render, and a browser should not have to be
# signed in to know the site's icon or to install it.
_OPEN_PATHS = frozenset({"/login", "/logout", "/favicon.ico", "/manifest.webmanifest", "/sw.js"})


def _is_open_path(path: str) -> bool:
    if path in _OPEN_PATHS:
        return True
    # The login page is server-rendered and pulls in no bundle, but the icons
    # are referenced by the manifest an unauthenticated browser may fetch.
    return path.startswith("/icon-")


def _client_id() -> str:
    """Who a failed login is counted against.

    REMOTE_ADDR is the Tailscale sidecar -- 10.89.4.3 on this deployment,
    confirmed from the server's own "Failed login from" line -- so every
    visitor on the internet shared a single counter. Eight bad guesses from
    anyone locked every real user out of the tool for fifteen minutes, which
    is a denial of service available to a stranger with curl.

    The proxy sets X-Forwarded-For; its first entry is the originating
    client. That header is attacker-controlled, so rotating it evades the
    throttle. Taking that trade deliberately: an attacker who evades it still
    has to guess a random password against PBKDF2 at 240,000 rounds a try,
    while the shared counter handed anyone a one-command outage.
    """
    forwarded = request.environ.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.environ.get("REMOTE_ADDR", "unknown")


@hook("before_request")
def _require_login():
    """Refuse anything that is not signed in.

    This RAISES rather than returns. bottle collects the return values of
    before_request hooks and throws them away -- trigger_hook builds a list
    and discards it -- so a hook that returns a 401 sets a status code and
    then lets the handler run anyway. An earlier version of this did exactly
    that: an unauthenticated GET / answered 401 and served the whole
    application, and /api/history answered 401 with the history in the body.
    Raising an HTTPResponse is what actually stops the request.
    """
    path = request.path

    # Fails closed. An operator who has not set a password gets an error, not
    # an open server -- the whole point of this file is that the alternative
    # silently publishes customer data.
    if not auth.is_configured():
        if _is_open_path(path):
            return
        raise HTTPResponse(
            body=_render_page(
                "Not configured",
                "<p>This server has no password set, so it is refusing every request.</p>"
                f"<p class='hint'>Set <code>{auth.PASSWORD_ENV}</code> in the environment and restart. "
                "Generate a value with <code>python -m audit_engine_web.setpassword</code>.</p>",
            ),
            status=503,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

    if _is_open_path(path):
        return
    if auth.session_is_valid(request.get_cookie(auth.COOKIE_NAME)):
        return

    # An API call gets a status its caller can act on; a browser gets the form.
    if path.startswith("/api/"):
        raise HTTPResponse(
            body=json.dumps({"success": False, "error": "Not signed in."}),
            status=401,
            headers={"Content-Type": "application/json"},
        )
    raise HTTPResponse(status=303, headers={"Location": "/login"})


def _render_page(title: str, body_html: str, *, status_note: str = "") -> str:
    """The login and error pages, rendered server-side.

    Deliberately standalone rather than part of the React app: this has to
    work before a visitor is allowed to fetch the bundle at all, and it should
    still render if that bundle is missing. The colours are the ones from
    tokens.css, copied rather than imported for the same reason.
    """
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GSS-MIS</title><link rel="icon" type="image/svg+xml" href="/favicon.ico">
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; min-height:100dvh; display:flex; align-items:center; justify-content:center;
         background:#0a0d12; color:#e9ecf1; padding:1.25rem;
         font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
  .box {{ width:100%; max-width:23rem; background:rgba(20,25,34,.65);
          border:1px solid rgba(58,68,82,.25); border-radius:14px; padding:1.75rem;
          box-shadow:0 1px 2px rgba(0,0,0,.24),0 8px 20px -6px rgba(0,0,0,.32); }}
  .brand {{ display:flex; align-items:center; gap:.6rem; margin-bottom:1.5rem; }}
  .mark {{ width:34px; height:34px; border-radius:9px; background:linear-gradient(135deg,#4c6fff,#5c7cfa);
           display:grid; place-items:center; font-weight:800; font-size:.8rem; }}
  h1 {{ font-size:1rem; margin:0; letter-spacing:-.01em; }}
  .sub {{ font-size:.7rem; color:#7c8695; margin-top:.15rem; }}
  label {{ display:block; font-size:.78rem; font-weight:600; color:#a6afbd; margin-bottom:.4rem; }}
  input {{ width:100%; min-height:44px; padding:.65rem .85rem; margin-bottom:1rem; font-size:.9rem;
           color:#e9ecf1; background:rgba(10,12,16,.8);
           border:1px solid rgba(58,68,82,.25); border-radius:6px; }}
  input:focus {{ outline:none; border-color:rgba(92,124,250,.4);
                 box-shadow:0 0 0 3px rgba(92,124,250,.15); }}
  button {{ width:100%; min-height:44px; border:0; border-radius:6px; background:#506cdb;
            color:#fff; font-weight:700; font-size:.85rem; cursor:pointer; }}
  button:hover {{ filter:brightness(1.1); }}
  .note {{ margin-bottom:1rem; padding:.7rem .8rem; border-radius:6px; font-size:.8rem;
           background:rgba(242,85,90,.1); border:1px solid rgba(242,85,90,.25); color:#f5828a; }}
  p {{ font-size:.85rem; color:#a6afbd; line-height:1.55; margin:0 0 .75rem; }}
  .hint {{ font-size:.78rem; color:#7c8695; }}
  code {{ font-family:ui-monospace,Menlo,monospace; font-size:.76rem; color:#a6afbd; }}
</style></head>
<body><div class="box">
  <div class="brand"><div class="mark">GM</div>
    <div><h1>GSS-MIS</h1><div class="sub">{title}</div></div></div>
  {f'<div class="note">{status_note}</div>' if status_note else ''}
  {body_html}
</div></body></html>"""


@route("/login", method=["GET", "POST"])
def login():
    response.content_type = "text/html; charset=utf-8"
    form = ("<form method=\"post\" action=\"/login\">"
            "<label for=\"u\">User</label>"
            f"<input id=\"u\" name=\"user\" autocomplete=\"username\" value=\"{auth.expected_user()}\">"
            "<label for=\"p\">Password</label>"
            "<input id=\"p\" name=\"password\" type=\"password\" autocomplete=\"current-password\" autofocus>"
            "<button type=\"submit\">Sign in</button></form>")

    if request.method == "GET":
        if auth.session_is_valid(request.get_cookie(auth.COOKIE_NAME)):
            response.status = 303
            response.set_header("Location", "/")
            return ""
        return _render_page("Sign in", form)

    client = _client_id()
    if auth.is_throttled(client):
        response.status = 429
        logger.warning("Login throttled for %s", client)
        return _render_page("Sign in", form, status_note="Too many attempts. Try again later.")

    user = (request.forms.get("user") or "").strip()
    password = request.forms.get("password") or ""
    if user == auth.expected_user() and auth.verify_password(password, os.environ.get(auth.PASSWORD_ENV, "")):
        auth.clear_failures(client)
        response.set_cookie(
            auth.COOKIE_NAME, auth.issue_session(),
            httponly=True,           # not readable from JavaScript, so XSS cannot lift it
            secure=True,             # only ever sent over TLS
            samesite="lax",          # not attached to cross-site form posts
            max_age=auth.SESSION_MAX_AGE, path="/",
        )
        response.status = 303
        response.set_header("Location", "/")
        return ""

    auth.note_failure(client)
    logger.warning("Failed login from %s", client)
    response.status = 401
    return _render_page("Sign in", form, status_note="Wrong user or password.")


@route("/logout", method=["GET", "POST"])
def logout():
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    response.status = 303
    response.set_header("Location", "/login")
    return ""


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

def _safe_upload_name(upload) -> str:
    """The uploaded file's own name, kept intact enough to still mean something.

    bottle's FileUpload.filename collapses every run of whitespace to a dash
    and drops anything outside [A-Za-z0-9-_.], so
    "Axis Bank POA Payment Mar26.xlsx" arrives as
    "Axis-Bank-POA-Payment-Mar26.xlsx" and "L & T Collection.xlsx" loses its
    ampersand altogether. Consolidation matches a workbook to its client by
    patterns written with real spaces -- "Axis Bank POA", "L & T Collection",
    "^RBL -" -- so every uploaded file fell through to a generic label made
    from the mangled name, and its configured column overrides were skipped.

    So this starts from raw_filename and keeps the characters those patterns
    depend on, while still being the only thing standing between a caller's
    string and a path on disk: basename only, no separators, no traversal, no
    control characters, no leading dot.
    """
    raw = getattr(upload, "raw_filename", "") or upload.filename or ""
    # Path separators first, both kinds, so nothing can steer out of the directory.
    raw = raw.replace("\\", "/").split("/")[-1]
    kept = "".join(c for c in raw if c.isalnum() or c in " &-_.()',")
    kept = " ".join(kept.split())          # collapse whitespace runs, strip ends
    kept = kept.replace("..", ".").lstrip(".")
    return kept[:200] or "upload.xlsx"


@route("/api/upload", method=["OPTIONS", "POST"])
def handle_upload():
    if request.method == "OPTIONS":
        return {}
    upload = request.files.get("file")
    if not upload:
        return {"success": False, "error": "No file provided"}
    safe_name = _safe_upload_name(upload)
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
        safe_name = _safe_upload_name(upload)
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
    # Same confinement /api/download and /api/preview already had. Without it
    # this read any workbook on the filesystem, not just the ones this server
    # is managing -- another tenant's upload included.
    denied = _reject_outside_workspace(abs_path)
    if denied:
        return denied
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
    denied = _reject_outside_workspace(Path(filepath))
    if denied:
        return denied
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


@route("/api/consolidate/run", method="POST")
def web_consolidate_run():
    """Consolidation, with the cleanup a bank run already had.

    /api/run is overridden here so its inputs are purged before and reaped
    after; consolidation went straight to the shared handler and got
    neither, so a customer's workbooks sat in the workspace until the idle
    sweeper happened to notice them.
    """
    from audit_engine.web.handlers import handle_consolidate_run

    data = dict(request.json or {})
    inputs = [f for f in (data.get("files") or []) if f]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data["output_dir"] = str(OUTPUT_DIR)

    cleared = _purge_workspace(keep_paths=inputs)
    if cleared:
        logger.info("Zero-trace: cleared %d item(s) left by the previous job", cleared)

    result = handle_consolidate_run(data)
    if isinstance(result, dict) and result.get("success"):
        from audit_engine.web.handlers import consolidation_tracker
        _reap_inputs_when_job_ends(inputs, still_running=lambda: consolidation_tracker.is_running)
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
