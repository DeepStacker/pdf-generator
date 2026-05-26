"""Bottle WSGI route definitions — thin routing layer only.

All business logic lives in imported handler functions and service modules.
Routes only parse input and delegate.
"""

import json
import time

import audit_engine.ui as ui_template
from audit_engine._version import VERSION
from audit_engine.lib.bottle import request, route
from audit_engine.web.handlers import (
    handle_browse_file,
    handle_browse_files,
    handle_browse_folder,
    handle_cancel,
    handle_config_save,
    handle_dashboard,
    handle_history,
    handle_history_clear,
    handle_open,
    handle_progress,
    handle_recent_clear,
    handle_run,
    handle_stats,
    handle_update_apply,
    handle_update_check,
    handle_update_install,
    handle_update_progress,
    handle_validate,
)


@route("/")
def serve_index() -> str:
    return ui_template.get_html(VERSION)


@route("/api/dashboard")
def api_dashboard() -> dict:
    return handle_dashboard()


@route("/api/config/save", method="POST")
def api_config_save() -> dict:
    return handle_config_save(request.json)


@route("/api/validate", method="POST")
def api_validate() -> dict:
    return handle_validate(request.json)


@route("/api/browse/file")
def api_browse_file() -> dict:
    return handle_browse_file()


@route("/api/browse/files")
def api_browse_files() -> dict:
    return handle_browse_files()


@route("/api/browse/folder")
def api_browse_folder() -> dict:
    return handle_browse_folder()


@route("/api/run", method="POST")
def api_run() -> dict:
    return handle_run(request.json)


@route("/api/progress")
def api_progress() -> dict:
    return handle_progress()


@route("/api/cancel")
def api_cancel() -> dict:
    return handle_cancel()


@route("/api/history")
def api_history() -> str:
    search = request.query.get("search", "").strip()
    return json.dumps(handle_history(search))


@route("/api/history/clear", method="POST")
def api_history_clear() -> dict:
    return handle_history_clear()


@route("/api/recent/clear", method="POST")
def api_recent_clear() -> dict:
    return handle_recent_clear()


@route("/api/stats")
def api_stats() -> dict:
    return handle_stats()


@route("/api/open", method="POST")
def api_open() -> dict:
    return handle_open(request.json)


# ---- Heartbeat ----
class _HeartbeatState:
    def __init__(self) -> None:
        self.last: float = time.time()

heartbeat = _HeartbeatState()


@route("/api/heartbeat")
def api_heartbeat() -> dict:
    heartbeat.last = time.time()
    return {"status": "ok"}


# ---- Auto-update ----
@route("/api/update/check")
def update_check() -> dict:
    return handle_update_check()


@route("/api/update/install", method="POST")
def update_install() -> dict:
    return handle_update_install()


@route("/api/update/progress")
def update_progress() -> dict:
    return handle_update_progress()


@route("/api/update/apply", method="POST")
def update_apply() -> dict:
    return handle_update_apply()
