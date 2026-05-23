import os
import pytest
import pandas as pd
from unittest.mock import patch
from equitas_logic import (
    clean_text, safe_float_numeric, safe_float, base_sheet_name,
    format_3, _merge_issue_only, _avg_int, run_equitas_stage1
)

def test_clean_text():
    assert clean_text("camelCaseString") == "camel Case String"
    assert clean_text("  Extra   Spaces  ") == "Extra Spaces"
    assert clean_text(float('nan')) == ""
    assert clean_text(None) == ""

def test_safe_float_numeric():
    assert safe_float_numeric("12.345") == 12.345
    assert safe_float_numeric("DIFF: 1.5") == 1.5
    assert safe_float_numeric("DIFF:-0.5") == -0.5
    assert safe_float_numeric(float('nan')) == 0.0
    assert safe_float_numeric(None) == 0.0
    assert safe_float_numeric("Invalid") == 0.0
    assert safe_float_numeric("") == 0.0

def test_safe_float():
    assert safe_float(12.345) == "12.345"
    assert safe_float("15.0") == "15"
    assert safe_float(float('nan')) == ""
    assert safe_float(None) == ""
    assert safe_float("Not a number") == "Not a number"

def test_base_sheet_name():
    assert base_sheet_name("BranchA_JSR") == "brancha"
    assert base_sheet_name("BranchA") == "brancha"
    assert base_sheet_name("  BRANCH_B_JSR  ") == "branch_b"

def test_format_3():
    assert format_3(5) == "5.000"
    assert format_3("12.3456") == "12.346"
    assert format_3("invalid") == "0.000"

def test_merge_issue_only():
    # Only returns issues, omits OK
    series = ["OK - no discrepancy", "Weight mismatch", "OK - no discrepancy", "Carat mismatch"]
    assert _merge_issue_only(series) == "Weight mismatch, Carat mismatch"
    
    # If all OK, returns OK
    series2 = ["OK - no discrepancy", "OK - no discrepancy"]
    assert _merge_issue_only(series2) == "OK - no discrepancy"

    # Duplicates removed
    series3 = ["Weight mismatch", "Weight mismatch"]
    assert _merge_issue_only(series3) == "Weight mismatch"

def test_avg_int():
    # Averages actual carat values, rounding to nearest int
    assert _avg_int(["22", "20"]) == 21
    assert _avg_int(["22.5", "21.5"]) == 22
    assert _avg_int([22, 20, "invalid"]) == 21
    assert _avg_int([0, ""]) == ""

def test_run_equitas_stage1_formatting_filters(tmp_path):
    # Mock build_master_dataframe to return a small DataFrame with 2 branches
    mock_df = pd.DataFrame({
        "SOLE_ID": [101, 102],
        "BRANCH_NAME": ["BranchA", "BranchB"],
        "SVS_LOAN_NO": ["L1", "L2"],
        "SR_NO": [1, 2],
        "CUSTOMER_NAME": ["Alice", "Bob"],
        "WEIGHT": [10.0, 20.0],
    })

    output_dir = str(tmp_path)

    # Test PDF ONLY format
    with patch("equitas_logic.build_master_dataframe", return_value=mock_df) as mock_build, \
         patch("equitas_logic.generate_branch_pdf", return_value="mock.pdf") as mock_gen_pdf, \
         patch("equitas_logic.generate_branch_excel", return_value="mock.xlsx") as mock_gen_excel:
        
        pdf_c, exc_c = run_equitas_stage1(
            "dummy_master.xlsx", output_dir, output_format="PDF ONLY", output_mode="FOLDER"
        )
        
        assert pdf_c > 0
        assert exc_c == 0
        mock_gen_pdf.assert_called()
        mock_gen_excel.assert_not_called()

    # Test EXCEL ONLY format
    with patch("equitas_logic.build_master_dataframe", return_value=mock_df) as mock_build, \
         patch("equitas_logic.generate_branch_pdf", return_value="mock.pdf") as mock_gen_pdf, \
         patch("equitas_logic.generate_branch_excel", return_value="mock.xlsx") as mock_gen_excel:
        
        pdf_c, exc_c = run_equitas_stage1(
            "dummy_master.xlsx", output_dir, output_format="EXCEL ONLY", output_mode="FOLDER"
        )
        
        assert pdf_c == 0
        assert exc_c > 0
        mock_gen_pdf.assert_not_called()
        mock_gen_excel.assert_called()

def test_run_equitas_stage1_packaging(tmp_path):
    mock_df = pd.DataFrame({
        "SOLE_ID": [101],
        "BRANCH_NAME": ["BranchA"],
        "SVS_LOAN_NO": ["L1"],
        "SR_NO": [1],
        "CUSTOMER_NAME": ["Alice"],
        "WEIGHT": [10.0],
    })

    # Test output_mode = "ZIP OF BOTH" (which is ZIP ONLY - raw folders deleted)
    output_dir = str(tmp_path / "zip_both")
    os.makedirs(output_dir, exist_ok=True)

    with patch("equitas_logic.build_master_dataframe", return_value=mock_df), \
         patch("equitas_logic.generate_branch_pdf", side_effect=lambda name, df, out_dir: (os.makedirs(out_dir, exist_ok=True), open(os.path.join(out_dir, "test.pdf"), "w").close(), os.path.join(out_dir, "test.pdf"))[2]), \
         patch("equitas_logic.generate_branch_excel", side_effect=lambda name, df, out_dir: (os.makedirs(out_dir, exist_ok=True), open(os.path.join(out_dir, "test.xlsx"), "w").close(), os.path.join(out_dir, "test.xlsx"))[2]):
        
        pdf_c, exc_c = run_equitas_stage1(
            "dummy_master.xlsx", output_dir, output_format="BOTH", output_mode="ZIP OF BOTH"
        )
        
        # Verify zip files created
        assert os.path.exists(os.path.join(output_dir, "output_pdfs.zip"))
        assert os.path.exists(os.path.join(output_dir, "output_excels.zip"))
        # Verify raw directories cleaned up
        assert not os.path.exists(os.path.join(output_dir, "output_pdfs"))
        assert not os.path.exists(os.path.join(output_dir, "output_excels"))

    # Test output_mode = "BOTH (FOLDER + ZIP OF PDF)" (keeps raw folders, zips only PDFs)
    output_dir2 = str(tmp_path / "folder_zip_pdf")
    os.makedirs(output_dir2, exist_ok=True)

    with patch("equitas_logic.build_master_dataframe", return_value=mock_df), \
         patch("equitas_logic.generate_branch_pdf", side_effect=lambda name, df, out_dir: (os.makedirs(out_dir, exist_ok=True), open(os.path.join(out_dir, "test.pdf"), "w").close(), os.path.join(out_dir, "test.pdf"))[2]), \
         patch("equitas_logic.generate_branch_excel", side_effect=lambda name, df, out_dir: (os.makedirs(out_dir, exist_ok=True), open(os.path.join(out_dir, "test.xlsx"), "w").close(), os.path.join(out_dir, "test.xlsx"))[2]):
        
        pdf_c, exc_c = run_equitas_stage1(
            "dummy_master.xlsx", output_dir2, output_format="BOTH", output_mode="BOTH (FOLDER + ZIP OF PDF)"
        )
        
        # Verify PDF zip created, Excel zip NOT created
        assert os.path.exists(os.path.join(output_dir2, "output_pdfs.zip"))
        assert not os.path.exists(os.path.join(output_dir2, "output_excels.zip"))
        # Verify BOTH raw directories preserved
        assert os.path.exists(os.path.join(output_dir2, "output_pdfs"))
        assert os.path.exists(os.path.join(output_dir2, "output_excels"))
