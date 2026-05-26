"""Application factory — creates and configures the Audit Engine WSGI app.

This is the single entry point for initializing the application.
All side effects (database init, route registration, logging) happen
through this factory, not at import time.
"""

import os
import signal
import threading
import time

from audit_engine._version import VERSION
from audit_engine.database import init_db
from audit_engine.lib.bottle import default_app
from audit_engine.utils.config import heartbeat as hb_config
from audit_engine.utils.platform import file_logger, setup_logging


def create_app(register_routes: bool = True) -> object:
    """Create and configure the Bottle WSGI application.

    Args:
        register_routes: If True (default), registers all API routes.
                        Set to False in tests that only need the package imported.

    Returns:
        The Bottle application instance.
    """
    log = setup_logging()
    log.info("Audit Engine v%s initializing...", VERSION)
    init_db()

    # Warm up the UI template cache so first page load is fast
    import audit_engine.ui  # noqa: F401

    app = default_app()

    # Request body size limit middleware (10 MB)
    _max_body = 10 * 1024 * 1024

    @app.hook("before_request")
    def _log_request() -> None:
        from audit_engine.lib.bottle import abort, request as _req  # noqa: I001
        raw_cl = _req.headers.get("Content-Length", "0")
        content_length = int(raw_cl) if raw_cl.strip() else 0
        if content_length > _max_body:
            abort(413, "Request body too large")
        log.info("--> %s %s", _req.method, _req.path)

    if register_routes:
        import audit_engine.web.routes  # noqa: F401 — registers routes on default_app

    return app


# ---- Heartbeat monitor (browser mode) ----
class _IPCMode:
    """Mutable boolean container so it can be imported by reference."""
    def __init__(self) -> None:
        self.enabled: bool = False

_ipc_mode = _IPCMode()
_shutdown_event = threading.Event()


def shutdown() -> None:
    """Signal graceful shutdown. Check with shutdown_requested()."""
    _shutdown_event.set()


def shutdown_requested() -> bool:
    """Return True if shutdown() was called."""
    return _shutdown_event.is_set()


def start_heartbeat_monitor() -> None:
    """Daemon thread that exits the process when the frontend stops sending heartbeats."""

    def _monitor() -> None:
        from audit_engine.web.routes import heartbeat as _hb

        time.sleep(30)
        while True:
            try:
                if _ipc_mode.enabled:
                    time.sleep(10)
                    continue
                if time.time() - _hb.last > hb_config.timeout:
                    file_logger.info("Heartbeat lost. Self-terminating.")
                    os.kill(os.getpid(), signal.SIGTERM)
                    return
                time.sleep(hb_config.interval)
            except Exception:
                file_logger.exception("Heartbeat monitor error")
                time.sleep(hb_config.interval)

    t = threading.Thread(target=_monitor, daemon=True)
    t.start()
