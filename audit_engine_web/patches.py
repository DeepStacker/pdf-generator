import logging

logger = logging.getLogger(__name__)


def apply_patches():
    import audit_engine.tasks.workers as workers_mod
    import audit_engine.utils.dialogs as dialogs_mod
    import audit_engine.utils.platform as platform_mod
    import audit_engine.web.handlers as handlers_mod
    import audit_engine.web.report_handlers as report_handlers_mod

    dialogs_mod.ask_file_dialog = lambda: ""
    dialogs_mod.ask_pdf_file_dialog = lambda: ""
    dialogs_mod.ask_files_dialog = lambda: []
    dialogs_mod.ask_directory_dialog = lambda: ""

    platform_mod.open_path = lambda _path: logger.info("open_path skipped (web mode): %s", _path)
    platform_mod.trigger_notification = lambda _title, _message: logger.debug("notification skipped (web mode): %s - %s", _title, _message)

    handlers_mod.ask_file_dialog = lambda: ""
    handlers_mod.ask_files_dialog = lambda: []
    handlers_mod.ask_directory_dialog = lambda: ""
    handlers_mod.open_path = lambda _path: logger.info("open_path skipped (web mode): %s", _path)
    handlers_mod.handle_browse_file = lambda: {"path": ""}
    handlers_mod.handle_browse_files = lambda: {"paths": []}
    handlers_mod.handle_browse_folder = lambda: {"path": ""}
    handlers_mod.handle_open = lambda _data: {"success": True}

    workers_mod.open_path = lambda _path: logger.info("open_path skipped (web mode, worker): %s", _path)
    workers_mod.trigger_notification = lambda _title, _message: logger.debug("notification skipped (web mode, worker): %s - %s", _title, _message)

    # The desktop Report Validator drives native dialogs and validates a path on
    # the local disk. Served over HTTP that would mean a dialog on the *server*
    # and arbitrary server-side file reads, so it is disabled entirely in web
    # mode — the browser UI uses /api/report/upload instead.
    _desktop_only = {"success": False, "error": "Not available in web mode - use the upload flow."}
    report_handlers_mod.ask_file_dialog = lambda: ""
    report_handlers_mod.ask_pdf_file_dialog = lambda: ""
    report_handlers_mod.open_path = lambda _path: logger.info("open_path skipped (web mode): %s", _path)
    report_handlers_mod.handle_report_browse = lambda: {"success": True, "path": ""}
    report_handlers_mod.handle_report_browse_pdf = lambda: {"success": True, "path": ""}
    report_handlers_mod.handle_report_run = lambda _data: dict(_desktop_only)
    report_handlers_mod.handle_report_open = lambda _data: dict(_desktop_only)
