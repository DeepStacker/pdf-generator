"""Background worker threads for IDFC, Equitas, and Arvog PDF generation."""

import logging
import os
import shutil
import threading
import time
import zipfile
from datetime import datetime

from audit_engine.database import get_config, log_generation
from audit_engine.services import arvog as arvog_bank
from audit_engine.services import equitas as equitas_logic
from audit_engine.services import idfc as pdf_logic
from audit_engine.tasks.tracker import ProgressTracker
from audit_engine.utils.platform import open_path, trigger_notification

logger = logging.getLogger(__name__)

global_tracker: ProgressTracker = ProgressTracker()
cancel_event: threading.Event = threading.Event()


def _cleanup_temp_mapped(inp_list: list[str]) -> None:
    for f in inp_list if isinstance(inp_list, list) else [inp_list]:
        if "mapped_" in os.path.basename(f) and ".temp_audit_engine" in f:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError:
                pass


def _format_size(total_size: int) -> str:
    return f"{total_size / 1024:.1f} KB" if total_size < 1024 * 1024 else f"{total_size / 1024 / 1024:.1f} MB"


def _make_summary(title: str, items: list[dict]) -> dict:
    return {"title": title, "items": items}


def worker_idfc_thread(inp: str | list[str], out_base: str, typ: str, output_mode: str, auto_open: bool, naming_pattern: str) -> None:
    try:
        inp_list = inp if isinstance(inp, list) else [inp]
        total_files = len(inp_list)

        global_tracker.log("INFO", f"Initializing IDFC Build: Found {total_files} master file(s).")

        _start_time = time.time()

        pdf_count = 0
        total_size = 0

        for idx, current_file in enumerate(inp_list, 1):
            if cancel_event.is_set():
                global_tracker.log("WARN", f"CANCELLED by user after processing {idx-1}/{total_files} files.")
                break

            global_tracker.update_pct((idx - 1) / total_files * 100, active_branch=f"File {idx}/{total_files}: {os.path.basename(current_file)}")
            global_tracker.log("INFO", f"=== File {idx}/{total_files}: {os.path.basename(current_file)} ===")

            curr_inp = os.path.abspath(os.path.normpath(current_file))
            curr_out_base = os.path.abspath(os.path.normpath(out_base))

            excel_name = os.path.splitext(os.path.basename(curr_inp))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            out = os.path.join(curr_out_base, f"{excel_name}_{timestamp}")
            out = os.path.abspath(os.path.normpath(out))
            os.makedirs(out, exist_ok=True)

            s, h, rows = pdf_logic.read_excel(curr_inp, lambda x: global_tracker.log("INFO", x))
            groups = pdf_logic.group_by_branch(rows)

            total_branches = len(groups)
            needs_zip = output_mode in ("ZIP ONLY", "BOTH")
            pdf_pct_max = 90.0 if needs_zip else 100.0

            for count, (c, br) in enumerate(sorted(groups.items()), 1):
                if cancel_event.is_set():
                    global_tracker.log("WARN", f"CANCELLED by user after {count}/{total_branches} branches.")
                    break

                name = str(br[0].get("CurrentBranchName", "Branch")).strip()
                st = str(br[0].get("State", "")).strip()
                safe_name = "".join(x for x in name if x.isalnum() or x in " -_").strip()
                if not safe_name:
                    safe_name = str(c)

                branch_part = safe_name
                type_part = typ
                filename = naming_pattern.replace("{branch}", branch_part).replace("{type}", type_part)
                filename = "".join(x for x in filename if x.isalnum() or x in " -_.").strip()
                if not filename.endswith(".pdf"):
                    filename += ".pdf"
                path = os.path.join(out, filename)
                path = os.path.abspath(os.path.normpath(path))

                inner_pct = (idx - 1) / total_files * 100 + (count / total_branches) * (1 / total_files) * pdf_pct_max
                global_tracker.update_pct(inner_pct, active_branch=f"File {idx}/{total_files} - {safe_name}")
                global_tracker.log("INFO", f"File {idx}/{total_files}: Building branch {safe_name}")
                pdf_logic.generate_pdf(typ, c, name, st, br, path)
                pdf_count += 1

            if needs_zip and not cancel_event.is_set():
                global_tracker.log("INFO", "Compressing PDF bundle...")
                zip_path = os.path.join(curr_out_base, f"{excel_name}_{timestamp}.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root_dir, _, files in os.walk(out):
                        for file in files:
                            zipf.write(os.path.join(root_dir, file), file)
                global_tracker.log("INFO", f"Saved ZIP archive to: {os.path.basename(zip_path)}")
                if output_mode == "ZIP ONLY":
                    shutil.rmtree(out, ignore_errors=True)

            for root_dir, _, files in os.walk(curr_out_base):
                for f in files:
                    if f.startswith(excel_name) and (f.endswith(".zip") or os.path.isdir(os.path.join(root_dir, f))):
                        total_size += os.path.getsize(os.path.join(root_dir, f)) if os.path.isfile(os.path.join(root_dir, f)) else 0

            if auto_open and total_files == 1 and os.path.exists(out):
                open_path(out)

        _cleanup_temp_mapped(inp_list)

        _elapsed = time.time() - _start_time
        log_generation(", ".join([os.path.basename(f) for f in inp_list]), pdf_count, out_base, f"IDFC Bulk {typ}", full_path="; ".join(inp_list))
        global_tracker.log("OK", f"SUCCESS: Completed {total_files} files, {pdf_count} Reports Created in {_elapsed:.1f}s.")
        global_tracker.update_pct(100.0)

        if auto_open and total_files > 1 and os.path.exists(out_base):
            open_path(out_base)

        global_tracker.summary = _make_summary("IDFC Bulk Generation Complete", [
            {"label": "Status", "value": "✓ Success"},
            {"label": "Audit Type", "value": f"IDFC {typ} Bulk"},
            {"label": "Files Processed", "value": f"{total_files} Master Excels"},
            {"label": "Total PDF Reports", "value": str(pdf_count)},
            {"label": "Total Time Taken", "value": f"{_elapsed:.1f}s"},
            {"label": "Total Output Size", "value": _format_size(total_size) if total_size > 0 else "0 KB"},
            {"label": "Staging Directory", "value": out_base}
        ])
        trigger_notification("Audit Engine Elite", f"✓ IDFC Bulk generation complete! Created {pdf_count} branch reports.")

    except Exception as e:
        global_tracker.log("ERROR", f"FAILURE: {e}")
        global_tracker.summary = {"title": "IDFC Bulk Generation Failed", "message": str(e)}
        trigger_notification("IDFC Generation Failed", f"✗ Batch compilation failed: {e}")
    finally:
        global_tracker.is_running = False


def worker_equitas_thread(inp: str | list[str], out_base: str, stage: str, equitas_format: str, equitas_pack: str) -> None:
    try:
        inp_list = inp if isinstance(inp, list) else [inp]
        total_files = len(inp_list)

        global_tracker.log("INFO", f"Initializing Equitas {stage} Build: Found {total_files} master file(s).")

        _start_time = time.time()

        item_count = 0
        total_size = 0

        for idx, current_file in enumerate(inp_list, 1):
            if cancel_event.is_set():
                global_tracker.log("WARN", f"CANCELLED by user after processing {idx-1}/{total_files} files.")
                break

            global_tracker.update_pct((idx - 1) / total_files * 100, active_branch=f"File {idx}/{total_files}: {os.path.basename(current_file)}")
            global_tracker.log("INFO", f"=== File {idx}/{total_files}: {os.path.basename(current_file)} ===")

            curr_inp = os.path.abspath(os.path.normpath(current_file))
            curr_out_base = os.path.abspath(os.path.normpath(out_base))

            excel_name = os.path.splitext(os.path.basename(curr_inp))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            out = os.path.join(curr_out_base, f"{excel_name}_EQ_{stage.replace(' ', '')}_{timestamp}")
            out = os.path.abspath(os.path.normpath(out))
            os.makedirs(out, exist_ok=True)

            if stage == "STAGE 1":
                pdf_c, exc_c = equitas_logic.run_equitas_stage1(
                    curr_inp, out,
                    lambda x, level="INFO": global_tracker.log(level, x),
                    cancel_event,
                    lambda pct: global_tracker.update_pct((idx - 1) / total_files * 100 + pct / total_files),
                    output_format=equitas_format, output_mode=equitas_pack
                )
                item_count += (pdf_c + exc_c)
            else:
                out_path = equitas_logic.run_equitas_stage2(
                    curr_inp, out,
                    lambda x, level="INFO": global_tracker.log(level, x),
                    cancel_event,
                    lambda pct: global_tracker.update_pct((idx - 1) / total_files * 100 + pct / total_files)
                )
                if out_path:
                    item_count += 1

            for root_dir, _, files in os.walk(out):
                for f in files:
                    total_size += os.path.getsize(os.path.join(root_dir, f))

            if get_config("auto_open", "True") == "True" and total_files == 1 and os.path.exists(out):
                open_path(out)

        _cleanup_temp_mapped(inp_list)

        _elapsed = time.time() - _start_time
        log_generation(", ".join([os.path.basename(f) for f in inp_list]), item_count, out_base, f"Equitas Bulk {stage}", full_path="; ".join(inp_list))
        global_tracker.log("OK", f"SUCCESS: Completed {total_files} files, {item_count} outputs created in {_elapsed:.1f}s.")
        global_tracker.update_pct(100.0)

        if get_config("auto_open", "True") == "True" and total_files > 1 and os.path.exists(out_base):
            open_path(out_base)

        global_tracker.summary = _make_summary(f"Equitas {stage} Complete", [
            {"label": "Status", "value": "✓ Success"},
            {"label": "Stage", "value": stage},
            {"label": "Files Processed", "value": f"{total_files} Master Excels"},
            {"label": "Generated Items", "value": str(item_count)},
            {"label": "Total Time Taken", "value": f"{_elapsed:.1f}s"},
            {"label": "Total File Size", "value": _format_size(total_size) if total_size > 0 else "0 KB"},
            {"label": "Output Directory", "value": out_base}
        ])
        trigger_notification("Audit Engine Elite", f"✓ Equitas Bulk {stage} complete! Generated {item_count} items.")

    except Exception as e:
        global_tracker.log("ERROR", f"FAILURE: {e}")
        global_tracker.summary = {"title": f"Equitas Bulk {stage} Failed", "message": str(e)}
        trigger_notification("Equitas Generation Failed", f"✗ Batch compilation failed: {e}")
    finally:
        global_tracker.is_running = False


def worker_arvog_thread(inp: str | list[str], out_base: str, auto_open: bool, output_format: str = "BOTH", output_mode: str = "FOLDER") -> None:
    try:
        inp_list = inp if isinstance(inp, list) else [inp]
        total_files = len(inp_list)

        global_tracker.log("INFO", f"Initializing Arvog Build: Found {total_files} master file(s).")

        _start_time = time.time()

        pdf_count = 0
        total_size = 0

        for idx, current_file in enumerate(inp_list, 1):
            if cancel_event.is_set():
                global_tracker.log("WARN", f"CANCELLED by user after processing {idx-1}/{total_files} files.")
                break

            global_tracker.update_pct((idx - 1) / total_files * 100, active_branch=f"File {idx}/{total_files}: {os.path.basename(current_file)}")
            global_tracker.log("INFO", f"=== File {idx}/{total_files}: {os.path.basename(current_file)} ===")

            curr_inp = os.path.abspath(os.path.normpath(current_file))
            curr_out_base = os.path.abspath(os.path.normpath(out_base))

            excel_name = os.path.splitext(os.path.basename(curr_inp))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            out = os.path.join(curr_out_base, f"{excel_name}_ARVOG_{timestamp}")
            out = os.path.abspath(os.path.normpath(out))
            os.makedirs(out, exist_ok=True)

            arvog_bank.process_excel(
                input_excel=curr_inp,
                output_dir=out,
                log_func=lambda msg: global_tracker.log("INFO", msg),
                output_format=output_format,
            )

            # Count generated items (PDFs and/or tall Excel sheet)
            curr_pdf_count = len([f for f in os.listdir(out) if f.endswith(".pdf")])
            pdf_count += curr_pdf_count

            # Packaging control: FOLDER, ZIP ONLY, or BOTH
            needs_zip = output_mode in ("ZIP ONLY", "BOTH")

            if needs_zip and not cancel_event.is_set():
                global_tracker.log("INFO", "Compressing Arvog bundle...")
                zip_path = os.path.join(curr_out_base, f"{excel_name}_ARVOG_{timestamp}.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root_dir, _, files in os.walk(out):
                        for file in files:
                            full_path = os.path.join(root_dir, file)
                            rel_path = os.path.relpath(full_path, out)
                            zipf.write(full_path, rel_path)
                global_tracker.log("INFO", f"Saved ZIP archive to: {os.path.basename(zip_path)}")
                if output_mode == "ZIP ONLY":
                    shutil.rmtree(out, ignore_errors=True)

            # Calculate total size of generated outputs
            for root_dir, _, files in os.walk(curr_out_base):
                for f in files:
                    if f.startswith(f"{excel_name}_ARVOG_{timestamp}"):
                        total_size += os.path.getsize(os.path.join(root_dir, f))

            if auto_open and total_files == 1:
                target_open = curr_out_base if output_mode == "ZIP ONLY" else out
                if os.path.exists(target_open):
                    open_path(target_open)

        _elapsed = time.time() - _start_time

        log_generation(", ".join([os.path.basename(f) for f in inp_list]), pdf_count, out_base, f"Arvog Bulk {output_format}", full_path="; ".join(inp_list))
        global_tracker.log("OK", f"SUCCESS: Completed {total_files} files, {pdf_count} Reports/Items Created in {_elapsed:.1f}s.")
        global_tracker.update_pct(100.0)

        if auto_open and total_files > 1 and os.path.exists(out_base):
            open_path(out_base)

        global_tracker.summary = _make_summary("Bulk Generation Complete", [
            {"label": "Status", "value": "✓ Success"},
            {"label": "Audit Type", "value": f"Arvog Bulk ({output_format})"},
            {"label": "Files Processed", "value": f"{total_files} Excel sheets"},
            {"label": "Total Reports/Items", "value": str(pdf_count)},
            {"label": "Packaging Mode", "value": output_mode},
            {"label": "Total Time", "value": f"{_elapsed:.1f}s"},
            {"label": "Total Output Size", "value": _format_size(total_size) if total_size > 0 else "0 KB"},
            {"label": "Output Directory", "value": out_base}
        ])
        trigger_notification("Audit Engine Elite", f"✓ Bulk generation complete! Created {pdf_count} branch reports.")

    except Exception as e:
        global_tracker.log("ERROR", f"FAILURE: {e}")
        global_tracker.summary = {"title": "Arvog Bulk Generation Failed", "message": str(e)}
        trigger_notification("Arvog Generation Failed", f"✗ Batch compilation failed: {e}")
    finally:
        global_tracker.is_running = False
