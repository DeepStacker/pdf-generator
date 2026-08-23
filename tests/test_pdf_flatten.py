"""Tests for the PDF flattener and its desktop/web surfaces.

Flattening must make a document permanent *without losing what it showed* —
a form's typed value has to survive as page content once the field is gone.
An upload must also leave nothing behind on the server.
"""

import json
import time
from pathlib import Path

import pytest
from pypdf import PdfReader

from audit_engine.services import pdf_flattener as fl
from audit_engine.web import flatten_handlers as fh


def make_form_pdf(path, *, with_form=True, with_link=True):
    """A PDF carrying the things flattening is meant to deal with."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    c.drawString(60, 780, "Audit Report")
    if with_form:
        form = c.acroForm
        form.textfield(name="branch", value="MUMBAI CENTRAL", x=60, y=730, width=220, height=20)
        form.textfield(name="auditor", value="R. SHARMA", x=60, y=700, width=220, height=20)
        form.checkbox(name="verified", checked=True, x=60, y=670)
    if with_link:
        c.linkURL("https://example.com", (60, 640, 200, 660), relative=0)
    c.save()
    return path


def fields_of(path):
    return list((PdfReader(str(path)).get_fields() or {}).keys())


def text_of(path):
    return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)


def annots_of(path):
    reader = PdfReader(str(path))
    return sum(len(p.get("/Annots") or []) for p in reader.pages)


@pytest.fixture
def form_pdf(tmp_path):
    return make_form_pdf(tmp_path / "form.pdf")


class TestFlattenCore:
    def test_form_fields_become_permanent_page_content(self, form_pdf):
        """The point of the feature: no fields left, but the values still show."""
        assert fields_of(form_pdf), "fixture should start with fields"

        result = fl.flatten_pdf(form_pdf)

        assert fields_of(result["output_path"]) == []
        text = text_of(result["output_path"])
        assert "MUMBAI CENTRAL" in text, "a filled value was lost - the flatten destroyed data"
        assert "R. SHARMA" in text

    def test_the_original_is_never_modified(self, form_pdf):
        before = form_pdf.read_bytes()
        fl.flatten_pdf(form_pdf)
        assert form_pdf.read_bytes() == before

    def test_output_lands_beside_the_source_by_default(self, form_pdf):
        result = fl.flatten_pdf(form_pdf)
        assert result["output_path"] == str(form_pdf.with_name("form_flattened.pdf"))
        assert Path(result["output_path"]).is_file()

    def test_explicit_output_path_is_honoured(self, form_pdf, tmp_path):
        out = tmp_path / "nested" / "done.pdf"
        result = fl.flatten_pdf(form_pdf, output_path=out)
        assert result["output_path"] == str(out)
        assert out.is_file()

    def test_links_are_removed(self, form_pdf):
        result = fl.flatten_pdf(form_pdf)
        assert result["links_removed"] >= 1
        assert annots_of(result["output_path"]) == 0

    def test_it_reports_what_it_did(self, form_pdf):
        result = fl.flatten_pdf(form_pdf)
        assert result["pages"] == 1
        assert result["fields_flattened"] == 3
        assert result["source_bytes"] > 0 and result["output_bytes"] > 0
        json.dumps(result)  # must cross the bridge

    def test_a_plain_pdf_without_forms_still_works(self, tmp_path):
        plain = make_form_pdf(tmp_path / "plain.pdf", with_form=False, with_link=False)
        result = fl.flatten_pdf(plain)
        assert result["fields_flattened"] == 0
        assert "Audit Report" in text_of(result["output_path"])

    def test_progress_runs_to_completion(self, form_pdf):
        seen = []
        fl.flatten_pdf(form_pdf, on_progress=lambda pct, msg="": seen.append(pct))
        assert seen and seen[-1] == 100
        assert seen == sorted(seen)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            fl.flatten_pdf(tmp_path / "nope.pdf")

    def test_a_non_pdf_is_a_clear_error(self, tmp_path):
        junk = tmp_path / "notreally.pdf"
        junk.write_text("this is not a pdf")
        with pytest.raises(fl.FlattenError, match="not a readable PDF"):
            fl.flatten_pdf(junk)

    def test_it_refuses_to_overwrite_the_original(self, form_pdf):
        with pytest.raises(fl.FlattenError, match="overwrite"):
            fl.flatten_pdf(form_pdf, output_path=form_pdf)


class TestSecureDelete:
    def test_the_file_is_gone(self, tmp_path):
        victim = tmp_path / "upload.pdf"
        victim.write_bytes(b"customer records" * 100)
        fl.secure_delete(victim)
        assert not victim.exists()

    def test_deleting_a_missing_file_is_harmless(self, tmp_path):
        fl.secure_delete(tmp_path / "never_existed.pdf")


class TestDesktopHandlers:
    @pytest.fixture(autouse=True)
    def _reset(self):
        fh.flatten_tracker.__init__()
        yield
        fh.flatten_tracker.__init__()

    def _wait(self, timeout=20.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not fh.flatten_tracker.is_running:
                return True
            time.sleep(0.05)
        return False

    def test_rejects_bad_input(self, tmp_path):
        assert fh.handle_flatten_run({})["success"] is False
        assert fh.handle_flatten_run({"filepath": str(tmp_path / "ghost.pdf")})["success"] is False

        not_pdf = tmp_path / "sheet.xlsx"
        not_pdf.write_text("x")
        assert "pdf" in fh.handle_flatten_run({"filepath": str(not_pdf)})["error"].lower()

    def test_full_run_cycle(self, form_pdf):
        assert fh.handle_flatten_run({"filepath": str(form_pdf)})["success"] is True
        assert self._wait(), "flatten did not finish"

        state = fh.handle_flatten_progress()
        assert state["error"] is None
        assert state["pct"] == 100
        assert state["summary"]["fields_flattened"] == 3
        assert Path(state["summary"]["output_path"]).is_file()
        assert any(log["level"] == "OK" for log in state["logs"])

    def test_a_broken_pdf_surfaces_as_an_error(self, tmp_path):
        junk = tmp_path / "broken.pdf"
        junk.write_text("nope")
        fh.handle_flatten_run({"filepath": str(junk)})
        assert self._wait()

        state = fh.handle_flatten_progress()
        assert state["error"]
        assert state["is_running"] is False, "tracker must not stay stuck"

    def test_second_run_refused_while_active(self, form_pdf):
        fh.flatten_tracker.is_running = True
        try:
            assert fh.handle_flatten_run({"filepath": str(form_pdf)})["success"] is False
        finally:
            fh.flatten_tracker.is_running = False

    def test_open_rejects_a_missing_path(self):
        assert fh.handle_flatten_open({})["success"] is False
        assert fh.handle_flatten_open({"path": "/definitely/not/here.pdf"})["success"] is False


class TestZeroSocketBridge:
    def test_end_to_end_over_the_bridge(self, form_pdf):
        from audit_engine.app import create_app
        from audit_engine.web.bridge import WebViewBridge

        create_app()
        bridge = WebViewBridge()
        fh.flatten_tracker.__init__()

        started = json.loads(bridge.fetch_proxy(
            "POST", "/api/flatten/run", json.dumps({"filepath": str(form_pdf)})
        ))
        assert started["success"] is True

        deadline = time.time() + 20
        payload = None
        while time.time() < deadline:
            payload = json.loads(bridge.fetch_proxy("GET", "/api/flatten/progress", ""))
            if not payload["is_running"]:
                break
            time.sleep(0.05)

        assert payload and payload["error"] is None
        assert Path(payload["summary"]["output_path"]).is_file()
