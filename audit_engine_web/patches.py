import logging

logger = logging.getLogger(__name__)


def apply_patches():
    import audit_engine.utils.dialogs as dialogs_mod
    import audit_engine.utils.platform as platform_mod
    import audit_engine.web.handlers as handlers_mod
    import audit_engine.tasks.workers as workers_mod

    dialogs_mod.ask_file_dialog = lambda: ""
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
