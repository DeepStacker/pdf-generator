"""Request handlers — business logic extracted from route definitions.

Keeps routes.py thin: routes only parse/validate input and delegate to handlers.
Handlers return plain dicts (JSON-serializable) that Bottle can return directly.
"""

import os
import sys
import time

from audit_engine.database.repos import config_repo, history_repo
from audit_engine.domain.enums import AuditType, BankType, EquitasFormat, EquitasStage, OutputMode
from audit_engine.tasks.workers import cancel_event, global_tracker, worker_arvog_thread, worker_equitas_thread, worker_idfc_thread
from audit_engine.updater.client import check_latest_release, download_update_worker, update_state
from audit_engine.utils.config import paths
from audit_engine.utils.dialogs import ask_directory_dialog, ask_file_dialog, ask_files_dialog
from audit_engine.utils.platform import open_path
from audit_engine.web.detect import detect_bank_from_file, peek_excel_data
from audit_engine.web.preprocess import preprocess_mapped_excel


def handle_dashboard() -> dict:
    total_sessions, total_pdfs = history_repo.stats()
    return {
        "bank": config_repo.get("bank", BankType.IDFC.value),
        "last_file": config_repo.get("last_file", ""),
        "out_path": config_repo.get("out_path", os.path.join(os.path.expanduser("~"), "Desktop")),
        "audit_type": config_repo.get("audit_type", "POA"),
        "output_mode": config_repo.get("pkg_mode", "BOTH"),
        "equitas_format": config_repo.get("equitas_format", "BOTH"),
        "equitas_pack": config_repo.get("equitas_pack", "FOLDER"),
        "arvog_format": config_repo.get("arvog_format", "BOTH"),
        "arvog_mode": config_repo.get("arvog_mode", "BOTH"),
        "auto_open": config_repo.get_bool("auto_open", True),
        "eq_auto_open": config_repo.get_bool("auto_open", True),
        "db_path": paths.db,
        "log_path": paths.log,
        "naming_pattern": config_repo.get("naming_pattern", "{branch}_{type}"),
        "recent_files": config_repo.get_recent_files(),
        "total_sessions": total_sessions,
        "total_pdfs": total_pdfs,
        "last_run": history_repo.last_run(),
        "selected_files_idfc": config_repo.get("selected_files_IDFC First Bank", "[]"),
        "selected_files_eq": config_repo.get("selected_files_Equitas Small Finance Bank", "[]"),
        "selected_files_arvog": config_repo.get("selected_files_Arvog Bank", "[]"),
    }


def handle_validate(data: dict) -> dict:
    filepath = data.get("filepath", "")
    if not filepath or not os.path.exists(filepath):
        return {"success": False, "error": "Spreadsheet file path does not exist."}

    detected_bank = detect_bank_from_file(filepath)
    headers, preview_rows = peek_excel_data(filepath)

    if detected_bank == BankType.IDFC.value:
        import audit_engine.services.idfc as pdf_logic
        valid, err = pdf_logic.validate_excel(filepath)
        if valid:
            s, h, rows = pdf_logic.read_excel(filepath, lambda x: None)
            groups = pdf_logic.group_by_branch(rows)
            return {
                "success": True, "detected_bank": detected_bank, "rows": len(rows),
                "branches": len(groups), "headers": headers, "preview": preview_rows,
            }
        return {"success": False, "error": err, "detected_bank": detected_bank, "headers": headers, "preview": preview_rows}

    if detected_bank == BankType.EQUITAS.value:
        import openpyxl

        import audit_engine.services.equitas as eq
        wb = openpyxl.load_workbook(filepath, read_only=True)
        sheets = wb.sheetnames
        wb.close()
        expected_stage = data.get("expected_stage")
        is_stage1 = any("JSR" in s.upper() or "NORMAL" in s.upper() for s in sheets) or len(sheets) > 1

        if expected_stage == "STAGE 2":
            if is_stage1:
                return {
                    "success": False, "error": "File appears to be Stage 1 (multi-sheet).",
                    "detected_bank": detected_bank, "headers": headers, "preview": preview_rows,
                }
            valid, err = eq.validate_equitas_stage2_file(filepath)
            return {
                "success": valid, "error": err, "detected_bank": detected_bank,
                "headers": headers, "preview": preview_rows,
            }
        if not is_stage1:
            return {
                "success": False, "error": "File appears to be Stage 2 (single sheet).",
                "detected_bank": detected_bank, "headers": headers, "preview": preview_rows,
            }
        valid, err = eq.validate_equitas_stage1_file(filepath)
        return {
            "success": valid, "error": err, "detected_bank": detected_bank,
            "headers": headers, "preview": preview_rows,
        }

    if detected_bank == BankType.ARVOG.value:
        import audit_engine.services.arvog as arvog_bank
        sheet_name, header_row = arvog_bank.detect_raw_excel(filepath)
        if sheet_name is not None:
            # Wide-format (raw) file with jewellery1/jewellery2
            import pandas as pd
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=header_row)
            branch_cols = [c for c in df.columns if str(c).strip().lower() == "branch"]
            bc = df[branch_cols[0]].nunique() if branch_cols else 1
            return {
                "success": True, "detected_bank": detected_bank, "rows": len(df),
                "branches": bc, "headers": headers, "preview": preview_rows,
            }
        # Fallback: try tall-format file (already converted / standard layout)
        try:
            valid_sheet = arvog_bank.detect_valid_sheet(filepath)
            import pandas as pd
            df = pd.read_excel(filepath, sheet_name=valid_sheet)
            branch_cols = [c for c in df.columns if str(c).strip().lower() == "branch"]
            bc = df[branch_cols[0]].nunique() if branch_cols else 1
            return {
                "success": True, "detected_bank": detected_bank, "rows": len(df),
                "branches": bc, "headers": headers, "preview": preview_rows,
            }
        except Exception:
            pass
        return {
            "success": False, "error": "Arvog file missing required columns.",
            "detected_bank": detected_bank, "headers": headers, "preview": preview_rows,
        }

    return {
        "success": False, "error": "Invalid bank format.",
        "detected_bank": None, "headers": headers, "preview": preview_rows,
    }


_VALID_OUTPUT_MODES = {e.value for e in OutputMode}
_VALID_AUDIT_TYPES = {e.value for e in AuditType}
_VALID_EQUITAS_STAGES = {e.value for e in EquitasStage}
_VALID_EQUITAS_FORMATS = {e.value for e in EquitasFormat}


def _validate_enum(value: str, valid_set: set[str], name: str) -> str | None:
    if value not in valid_set:
        return f"Invalid {name}: {value!r}. Valid values: {', '.join(sorted(valid_set))}"
    return None


def handle_run(data: dict) -> dict:
    if global_tracker.is_running:
        return {"success": False, "error": "A generation thread is already active."}

    bank: str = str(data.get("bank") or "")
    filepath_raw: object = data.get("filepath")
    out_path: str = str(data.get("out_path") or "")
    auto_open = bool(data.get("auto_open", True))
    naming_pattern: str = str(data.get("naming_pattern", "{branch}_{type}"))

    if bank == BankType.IDFC.value:
        err = _validate_enum(str(data.get("audit_type", "POA")), _VALID_AUDIT_TYPES, "audit_type")
        if err:
            return {"success": False, "error": err}
        err = _validate_enum(str(data.get("output_mode", "BOTH")), _VALID_OUTPUT_MODES, "output_mode")
        if err:
            return {"success": False, "error": err}
    elif bank == BankType.EQUITAS.value:
        err = _validate_enum(str(data.get("equitas_stage", "STAGE 1")), _VALID_EQUITAS_STAGES, "equitas_stage")
        if err:
            return {"success": False, "error": err}
        err = _validate_enum(str(data.get("equitas_format", "BOTH")), _VALID_EQUITAS_FORMATS, "equitas_format")
        if err:
            return {"success": False, "error": err}
    elif bank == BankType.ARVOG.value:
        err = _validate_enum(str(data.get("arvog_format", "BOTH")), _VALID_EQUITAS_FORMATS, "arvog_format")
        if err:
            return {"success": False, "error": err}
        err = _validate_enum(str(data.get("arvog_mode", "BOTH")), _VALID_OUTPUT_MODES, "arvog_mode")
        if err:
            return {"success": False, "error": err}

    if isinstance(filepath_raw, str):
        if not filepath_raw or not os.path.exists(filepath_raw):
            return {"success": False, "error": f"File missing: {filepath_raw}"}
        actual_filepath: str | list[str] = filepath_raw
        config_repo.set("last_file", filepath_raw)
        config_repo.add_recent_file(filepath_raw)
    elif isinstance(filepath_raw, list):
        if not filepath_raw:
            return {"success": False, "error": "No files provided."}
        for f in filepath_raw:
            if not f or not os.path.exists(f):
                return {"success": False, "error": f"File missing: {f}"}
        actual_filepath = list(filepath_raw)
        config_repo.set("last_file", filepath_raw[0])
        config_repo.add_recent_file(filepath_raw[0])
    else:
        return {"success": False, "error": "Invalid filepath format."}
    if not out_path or not os.path.exists(out_path):
        return {"success": False, "error": "Output directory invalid."}

    config_repo.set("bank", bank)
    config_repo.set("out_path", out_path)

    cancel_event.clear()
    global_tracker.reset()

    column_mappings = data.get("column_mappings")
    if column_mappings:
        if isinstance(actual_filepath, list):
            actual_filepath = [preprocess_mapped_excel(f, column_mappings, bank) for f in actual_filepath]
        else:
            actual_filepath = preprocess_mapped_excel(actual_filepath, column_mappings, bank)

    import threading

    if bank == BankType.IDFC.value:
        config_repo.set("audit_type", str(data.get("audit_type", "POA")))
        config_repo.set("pkg_mode", str(data.get("output_mode", "BOTH")))
        t = threading.Thread(
            target=worker_idfc_thread,
            args=(actual_filepath, out_path, str(data.get("audit_type", "POA")),
                  str(data.get("output_mode", "BOTH")), auto_open, naming_pattern),
            daemon=True,
        )
    elif bank == BankType.ARVOG.value:
        config_repo.set("arvog_format", str(data.get("arvog_format", "BOTH")))
        config_repo.set("arvog_mode", str(data.get("arvog_mode", "BOTH")))
        t = threading.Thread(
            target=worker_arvog_thread,
            args=(actual_filepath, out_path, auto_open,
                  str(data.get("arvog_format", "BOTH")), str(data.get("arvog_mode", "BOTH"))),
            daemon=True,
        )
    else:
        config_repo.set("equitas_format", str(data.get("equitas_format", "BOTH")))
        config_repo.set("equitas_pack", str(data.get("equitas_pack", "FOLDER")))
        t = threading.Thread(
            target=worker_equitas_thread,
            args=(actual_filepath, out_path, str(data.get("equitas_stage", "STAGE 1")),
                  str(data.get("equitas_format", "BOTH")), str(data.get("equitas_pack", "FOLDER"))),
            daemon=True,
        )
    t.start()
    return {"success": True}


def handle_progress() -> dict:
    return global_tracker.snapshot()


def handle_cancel() -> dict:
    cancel_event.set()
    global_tracker.cancel_requested = True
    return {"success": True}


def handle_history(search: str = "") -> list[dict]:
    return [
        {
            "id": e.id, "timestamp": e.timestamp, "excel_name": e.excel_name,
            "pdf_count": e.pdf_count, "output_path": e.output_path,
            "audit_type": e.audit_type, "full_path": e.full_path,
        }
        for e in history_repo.list(search)
    ]


def handle_history_clear() -> dict:
    history_repo.clear()
    return {"success": True}


def handle_recent_clear() -> dict:
    config_repo.clear_recent_files()
    return {"success": True}


def handle_stats() -> dict:
    types, trend = history_repo.analytics()
    total_sessions, total_pdfs = history_repo.stats()
    return {
        "distribution": types,
        "trend": [list(row) for row in trend],
        "total_sessions": total_sessions,
        "total_pdfs": total_pdfs,
        "total_excels": history_repo.total_unique_excels(),
    }


_ALLOWED_CONFIG_KEYS = frozenset({
    "bank", "last_file", "out_path", "audit_type", "pkg_mode", "output_mode",
    "equitas_format", "equitas_pack", "auto_open", "naming_pattern",
    "selected_files_IDFC First Bank", "selected_files_Equitas Small Finance Bank",
    "selected_files_Arvog Bank", "arvog_format", "arvog_mode",
})


def handle_config_save(data: dict) -> dict:
    key = data.get("key", "")
    if key not in _ALLOWED_CONFIG_KEYS:
        return {"success": False, "error": f"Unknown config key: {key}"}
    config_repo.set(key, str(data.get("value", "")))
    return {"success": True}


def handle_browse_file() -> dict:
    return {"path": ask_file_dialog()}


def handle_browse_files() -> dict:
    return {"paths": ask_files_dialog()}


def handle_browse_folder() -> dict:
    return {"path": ask_directory_dialog()}


def handle_open(data: dict) -> dict:
    path = data.get("path", "")
    if path and os.path.exists(path):
        open_path(path)
    return {"success": True}


def handle_update_check(force: bool = False) -> dict:
    return check_latest_release(force=force)


def handle_update_install() -> dict:
    if not getattr(sys, "frozen", False):
        return {"success": False, "error": "Binary updates are not supported in development mode. Use 'git pull' to update."}
    if not update_state.binary_url:
        return {"success": False, "error": "No update staged."}
    if not update_state.is_downloading:
        import threading
        threading.Thread(target=download_update_worker, args=(update_state.expected_sha256,), daemon=True).start()
    return {"success": True}


def handle_update_progress() -> dict:
    return {"pct": update_state.progress_pct, "is_downloading": update_state.is_downloading, "success": update_state.success, "error": update_state.error}


def handle_update_apply() -> dict:
    if not getattr(sys, "frozen", False):
        return {"success": False, "error": "Cannot apply update in development mode."}
    import threading
    def _apply():
        time.sleep(1)
        if update_state.staged_bat == "IN_PLACE_UPDATE":
            import os
            os._exit(0)
        from audit_engine.updater.client import _restart_app
        _restart_app()
    threading.Thread(target=_apply, daemon=True).start()
    return {"success": True}
