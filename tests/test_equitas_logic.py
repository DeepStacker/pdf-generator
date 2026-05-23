import os
import pytest
import pandas as pd
from equitas_logic import (
    clean_text, safe_float_numeric, safe_float, base_sheet_name,
    format_3, _merge_issue_only, _avg_int
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
