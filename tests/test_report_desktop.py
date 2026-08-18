"""Tests for the offline/desktop Report Validator path.

The desktop build must validate reports with no HTTP server and no sockets of
any kind: the UI talks to Python through the in-process WebViewBridge, passing
JSON strings only. These tests drive that exact path.
"""

import json
import time

import openpyxl
import pytest

from audit_engine.services import report_validator as rv
from audit_engine.web import report_handlers as rh
from tests.test_report_validator import KEY_TO_COL, SHEET, good_row, make_workbook  # noqa: F401


def _wait_idle(timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not rh.report_tracker.is_running:
            return True
        time.sleep(0.05)
    return False


@pytest.fixture(autouse=True)
def _reset_tracker():
    rh.report_tracker.__init__()
    yield
    rh.report_tracker.__init__()


class TestValidateWorkbook:
    """The shared core both the desktop app and web server call."""

    def test_writes_output_beside_source_by_default(self, tmp_path):
        src = tmp_path / "MyBranch.xlsx"
        make_workbook(src, [good_row("P01"), good_row("P02")])

        result = rv.validate_workbook(src)

        assert result["output_path"] == str(tmp_path / "TESTBR_Audit-MIS_UNKNOWN_DATE.xlsx")
        assert (tmp_path / "TESTBR_Audit-MIS_UNKNOWN_DATE.xlsx").exists()
        assert result["total_issues"] == 0
        assert result["rows_scanned"] == 2
        assert result["pdf_applied"] is False

    def test_explicit_output_path_is_honoured(self, tmp_path):
        src = tmp_path / "in.xlsx"
        make_workbook(src, [good_row("P01")])
        out = tmp_path / "nested" / "custom.xlsx"

        result = rv.validate_workbook(src, output_path=out)

        assert result["output_path"] == str(out)
        assert out.exists()

    def test_progress_callback_reaches_completion(self, tmp_path):
        src = tmp_path / "in.xlsx"
        make_workbook(src, [good_row("P01")])
        seen = []

        rv.validate_workbook(src, on_progress=lambda pct, msg=None: seen.append(pct))

        assert seen and seen[0] <= 15 and seen[-1] == 100
        assert seen == sorted(seen), "progress must be monotonic"

    def test_no_preview_payload_unless_requested(self, tmp_path):
        src = tmp_path / "in.xlsx"
        make_workbook(src, [good_row("P01")])

        assert "rows" not in rv.validate_workbook(src)
        assert "rows" in rv.validate_workbook(src, build_preview=True)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            rv.validate_workbook(tmp_path / "nope.xlsx")

    def test_wrong_sheet_raises_keyerror_naming_sheets(self, tmp_path):
        src = tmp_path / "wrong.xlsx"
        wb = openpyxl.Workbook()
        wb.active.title = "Some Other Sheet"
        wb.save(src)
        wb.close()

        with pytest.raises(KeyError, match="Some Other Sheet"):
            rv.validate_workbook(src)


class TestDesktopHandlers:
    def test_run_rejects_missing_and_bad_input(self, tmp_path):
        assert rh.handle_report_run({})["success"] is False
        assert rh.handle_report_run({"filepath": str(tmp_path / "ghost.xlsx")})["success"] is False

        xls = tmp_path / "legacy.xls"
        xls.write_text("not really excel")
        assert "xlsx" in rh.handle_report_run({"filepath": str(xls)})["error"].lower()

    def test_full_run_and_progress_cycle(self, tmp_path):
        src = tmp_path / "MyBranch.xlsx"
        rows = [good_row(f"P{i:02d}") for i in range(1, 6)]
        rows[1]["tare"] = 15.0  # tare < GDR gross
        make_workbook(src, rows)

        assert rh.handle_report_run({"filepath": str(src)})["success"] is True
        assert _wait_idle(), "validation did not finish"

        p = rh.handle_report_progress()
        assert p["error"] is None
        assert p["pct"] == 100
        assert p["is_running"] is False
        assert p["summary"]["summary"]["tare_less_than_weight"] == 2
        assert (tmp_path / "TESTBR_Audit-MIS_UNKNOWN_DATE.xlsx").exists()
        assert any(log["level"] == "OK" for log in p["logs"])

    def test_missing_sheet_surfaces_as_error_not_crash(self, tmp_path):
        src = tmp_path / "wrong.xlsx"
        wb = openpyxl.Workbook()
        wb.active.title = "Nope"
        wb.save(src)
        wb.close()

        rh.handle_report_run({"filepath": str(src)})
        assert _wait_idle()

        p = rh.handle_report_progress()
        assert p["error"] and "Nope" in p["error"]
        assert p["is_running"] is False, "tracker must not stay stuck running after a failure"

    def test_second_run_refused_while_one_is_active(self, tmp_path):
        src = tmp_path / "in.xlsx"
        make_workbook(src, [good_row("P01")])
        rh.report_tracker.is_running = True
        try:
            assert rh.handle_report_run({"filepath": str(src)})["success"] is False
        finally:
            rh.report_tracker.is_running = False

    def test_stale_pdf_path_is_ignored_not_fatal(self, tmp_path):
        src = tmp_path / "in.xlsx"
        make_workbook(src, [good_row("P01")])

        assert rh.handle_report_run({
            "filepath": str(src), "pdf_path": str(tmp_path / "gone.pdf"),
        })["success"] is True
        assert _wait_idle()
        p = rh.handle_report_progress()
        assert p["error"] is None
        assert p["summary"]["pdf_applied"] is False

    def test_open_rejects_missing_path(self):
        assert rh.handle_report_open({})["success"] is False
        assert rh.handle_report_open({"path": "/definitely/not/here.xlsx"})["success"] is False


class TestZeroSocketBridge:
    """Drive the endpoints exactly as the desktop JS does — no socket involved."""

    def test_end_to_end_over_bridge(self, tmp_path):
        from audit_engine.app import create_app
        from audit_engine.web.bridge import WebViewBridge

        create_app()
        bridge = WebViewBridge()

        src = tmp_path / "MyBranch.xlsx"
        rows = [good_row(f"P{i:02d}") for i in range(1, 5)]
        rows[2]["status"] = "CLOSED"
        make_workbook(src, rows)

        started = json.loads(bridge.fetch_proxy(
            "POST", "/api/report/run", json.dumps({"filepath": str(src), "pdf_path": ""})
        ))
        assert started["success"] is True

        deadline = time.time() + 15
        payload = None
        while time.time() < deadline:
            payload = json.loads(bridge.fetch_proxy("GET", "/api/report/progress", ""))
            if not payload["is_running"]:
                break
            time.sleep(0.05)

        assert payload is not None and payload["is_running"] is False
        assert payload["error"] is None
        assert payload["summary"]["total_issues"] > 0
        assert (tmp_path / "TESTBR_Audit-MIS_UNKNOWN_DATE.xlsx").exists()

    def test_run_response_is_json_serializable(self, tmp_path):
        """Everything crossing the bridge must survive json.dumps (it is a string channel)."""
        src = tmp_path / "in.xlsx"
        rows = [good_row("P01")]
        rows[0]["sanction_date"] = __import__("datetime").date(2026, 5, 1)
        make_workbook(src, rows)

        rh.handle_report_run({"filepath": str(src)})
        assert _wait_idle()
        json.dumps(rh.handle_report_progress())  # must not raise


class TestPdfIsTrulyOptional:
    """A missing/unreadable PDF must never cost the user their validated file.

    The packaged Windows build shipped without pypdf bundled, and because the
    import sat outside the try block a ModuleNotFoundError aborted the whole
    run — the user got no output at all for an optional convenience feature.
    """

    def test_missing_pypdf_degrades_instead_of_failing(self, tmp_path, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def no_pypdf(name, *args, **kwargs):
            if name == "pypdf" or name.startswith("pypdf."):
                raise ImportError("No module named 'pypdf'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", no_pypdf)

        pdf = tmp_path / "seq.pdf"
        pdf.write_bytes(b"%PDF-1.4 not really a pdf")
        src = tmp_path / "in.xlsx"
        make_workbook(src, [good_row("P01"), good_row("P02")])

        # Must not raise, and must still produce the validated workbook.
        result = rv.validate_workbook(src, pdf_path=str(pdf))

        assert result["pdf_applied"] is False
        assert result["pdf_warning"]
        assert (tmp_path / "TESTBR_Audit-MIS_UNKNOWN_DATE.xlsx").exists()

    def test_extract_accounts_never_raises(self, tmp_path):
        junk = tmp_path / "junk.pdf"
        junk.write_bytes(b"definitely not a pdf")
        assert rv.extract_accounts_from_pdf(str(junk)) == []
        assert rv.extract_accounts_from_pdf(str(tmp_path / "nonexistent.pdf")) == []

    def test_pdf_applied_reflects_reality_not_just_presence(self, tmp_path):
        """A supplied-but-unusable PDF must report pdf_applied=False."""
        pdf = tmp_path / "empty.pdf"
        pdf.write_bytes(b"not a pdf")
        src = tmp_path / "in.xlsx"
        make_workbook(src, [good_row("P01")])

        result = rv.validate_workbook(src, pdf_path=str(pdf))
        assert result["pdf_applied"] is False, "must not claim the PDF was applied"
        assert result["pdf_warning"]

    def test_desktop_worker_surfaces_the_warning(self, tmp_path):
        pdf = tmp_path / "bad.pdf"
        pdf.write_bytes(b"not a pdf")
        src = tmp_path / "in.xlsx"
        make_workbook(src, [good_row("P01")])

        rh.handle_report_run({"filepath": str(src), "pdf_path": str(pdf)})
        assert _wait_idle()

        p = rh.handle_report_progress()
        assert p["error"] is None, "an unusable PDF must not fail the run"
        assert any(log["level"] == "WARN" for log in p["logs"]), "user must be told the PDF was ignored"
