import logging

logger = logging.getLogger(__name__)

# What each patched name held before web mode replaced it.
#
# apply_patches() rewires desktop-only behaviour across a dozen modules, and
# it used to be a one-way door: importing the web server put the whole
# process into web mode for good. In the test suite that made the order of
# files matter -- anything importing the server before the desktop tests made
# them fail, because handle_flatten_run and friends had been replaced with
# "Not available in web mode". Recording the originals makes the switch
# reversible, so a test can put the process back.
_originals: dict[tuple[object, str], object] = {}


def _patch(module, name, value):
    for target in _targets(module, name):
        key = (target, name)
        if key not in _originals:
            _originals[key] = getattr(target, name, None)
        setattr(target, name, value)


def _targets(module, name):
    """Every module holding a reference to this name.

    routes.py does `from ... import handle_report_run` at import time, and
    create_app() imports it *after* apply_patches() has run -- so it captures
    the patched function as its own binding. Patching only the defining
    module therefore looks complete and is not: reverting restored the
    source while the route kept calling the stub. Same import-binding trap
    that once left web mode still writing history.
    """
    yield module
    try:
        import audit_engine.web.routes as routes_mod
    except Exception:
        return
    if routes_mod is not module and hasattr(routes_mod, name):
        yield routes_mod


def revert_patches():
    """Put every patched name back. Used by the tests, not by the server."""
    for (module, name), original in _originals.items():
        setattr(module, name, original)
    _originals.clear()


def apply_patches():
    import audit_engine.tasks.workers as workers_mod
    import audit_engine.database.legacy as legacy_mod
    import audit_engine.utils.dialogs as dialogs_mod
    import audit_engine.utils.platform as platform_mod
    import audit_engine.web.handlers as handlers_mod
    import audit_engine.web.arvog_rebuild_handlers as arvog_rebuild_mod
    import audit_engine.web.flatten_handlers as flatten_handlers_mod
    import audit_engine.web.report_handlers as report_handlers_mod

    _patch(dialogs_mod, 'ask_file_dialog', lambda: "")
    _patch(dialogs_mod, 'ask_pdf_file_dialog', lambda: "")
    _patch(dialogs_mod, 'ask_files_dialog', lambda: [])
    _patch(dialogs_mod, 'ask_directory_dialog', lambda: "")

    _patch(platform_mod, 'open_path', lambda _path: logger.info("open_path skipped (web mode): %s", _path))
    _patch(platform_mod, 'trigger_notification', lambda _title, _message: logger.debug("notification skipped (web mode): %s - %s", _title, _message))

    _patch(handlers_mod, 'ask_file_dialog', lambda: "")
    _patch(handlers_mod, 'ask_files_dialog', lambda: [])
    _patch(handlers_mod, 'ask_directory_dialog', lambda: "")
    _patch(handlers_mod, 'open_path', lambda _path: logger.info("open_path skipped (web mode): %s", _path))
    _patch(handlers_mod, 'handle_browse_file', lambda: {"path": ""})
    _patch(handlers_mod, 'handle_browse_files', lambda: {"paths": []})
    _patch(handlers_mod, 'handle_browse_folder', lambda: {"path": ""})
    _patch(handlers_mod, 'handle_open', lambda _data: {"success": True})

    _patch(workers_mod, 'open_path', lambda _path: logger.info("open_path skipped (web mode, worker): %s", _path))
    _patch(workers_mod, 'trigger_notification', lambda _title, _message: logger.debug("notification skipped (web mode, worker): %s - %s", _title, _message))

    # The desktop Report Validator drives native dialogs and validates a path on
    # the local disk. Served over HTTP that would mean a dialog on the *server*
    # and arbitrary server-side file reads, so it is disabled entirely in web
    # mode — the browser UI uses /api/report/upload instead.
    _desktop_only = {"success": False, "error": "Not available in web mode - use the upload flow."}
    _patch(report_handlers_mod, 'ask_file_dialog', lambda: "")
    _patch(report_handlers_mod, 'ask_pdf_file_dialog', lambda: "")
    _patch(report_handlers_mod, 'open_path', lambda _path: logger.info("open_path skipped (web mode): %s", _path))
    _patch(report_handlers_mod, 'handle_report_browse', lambda: {"success": True, "path": ""})
    _patch(report_handlers_mod, 'handle_report_browse_pdf', lambda: {"success": True, "path": ""})
    _patch(report_handlers_mod, 'handle_report_run', lambda _data: dict(_desktop_only))
    _patch(report_handlers_mod, 'handle_report_open', lambda _data: dict(_desktop_only))

    # The desktop flatten handlers drive a native dialog and read a path from
    # the local disk. Served over HTTP that would mean a dialog on the server
    # and arbitrary server-side file access, so they are disabled here — the
    # browser uses the upload endpoint instead.
    _patch(flatten_handlers_mod, 'ask_pdf_file_dialog', lambda: "")
    _patch(flatten_handlers_mod, 'open_path', lambda _path: logger.info("open_path skipped (web mode): %s", _path))
    _patch(flatten_handlers_mod, 'handle_flatten_browse', lambda: {"success": True, "path": ""})
    _patch(flatten_handlers_mod, 'handle_flatten_run', lambda _data: dict(_desktop_only))
    _patch(flatten_handlers_mod, 'handle_flatten_open', lambda _data: dict(_desktop_only))

    # Likewise the Arvog rebuild: a native dialog and a path on the local disk.
    # Over HTTP that would be a dialog on the server and server-side file
    # access, so the browser uses the upload endpoint instead.
    _patch(arvog_rebuild_mod, 'ask_file_dialog', lambda: "")
    _patch(arvog_rebuild_mod, 'open_path', lambda _path: logger.info("open_path skipped (web mode): %s", _path))
    _patch(arvog_rebuild_mod, 'handle_arvog_rebuild_browse', lambda: {"success": True, "path": ""})
    _patch(arvog_rebuild_mod, 'handle_arvog_rebuild_run', lambda _data: dict(_desktop_only))
    _patch(arvog_rebuild_mod, 'handle_arvog_rebuild_open', lambda _data: dict(_desktop_only))

    # The run history is a single-user feature on a single-user machine. Served
    # from a shared box it records one visitor's workbook name, and its full
    # path, for the next visitor to read back out of /api/history -- long after
    # the file itself has been deleted. A workbook name is customer data: it
    # routinely carries the branch and the date, sometimes the customer.
    #
    # So nothing is written here. The desktop app is unaffected and keeps its
    # history; the browser's History screen simply stays empty.
    def _skip_history(*_a, **_k):
        logger.debug("history write skipped (web mode)")

    # Both bindings. workers.py does `from audit_engine.database import
    # log_generation` at import time, so it holds its own reference and
    # patching only the source module left the real function being called --
    # which is exactly what happened: filenames kept landing in the history
    # table after this patch was supposedly in place. Verified by asserting on
    # workers_mod.log_generation, not on legacy_mod's.
    _patch(legacy_mod, 'log_generation', _skip_history)
    _patch(workers_mod, 'log_generation', _skip_history)

    # The service logs still name the workbook on the way in, and audit_engine.log
    # outlives the file. That log is on the server's own disk and no route can
    # read it -- the download and preview routes refuse anything outside the
    # managed directories -- so it is left alone rather than patched globally.
