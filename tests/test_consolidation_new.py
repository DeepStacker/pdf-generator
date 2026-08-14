"""
Unit and Integration Test Suite for Mar'26 Consolidation.
"""
import os
import sys

import pandas as pd
import pytest

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from audit_engine.consolidator import consolidate as c  # noqa: E402 - needs the sys.path setup above


def test_production_consolidation_total_pay_and_counts():
    """Verify that running full consolidation yields exact target totals.

    Data-dependent: this asserts against the real Mar'26 source workbooks,
    which are not committed (``sources/`` is gitignored). Skip rather than
    fail wherever they are absent, e.g. CI and fresh clones.
    """
    mapping_mgr = c.ColumnMappingManager()

    # Process only production source files (excluding test fixtures)
    files = sorted([
        f for f in os.listdir(c.SOURCE_DIR)
        if f.endswith(('.xlsx', '.XLSX', '.xls'))
        and not f.startswith('.')
        and not f.startswith('test_')
        and f not in ("Feb'26 consolidated.xlsx", "Mar'26 consolidated.xlsx", "consolidate.py")
    ])

    if not files:
        pytest.skip(f"production source workbooks not present in {c.SOURCE_DIR}")

    all_pt_rows = []
    all_md_rows = []

    for fname in files:
        if fname == "Payment Tracker Mar26.xlsx":
            continue

        fpath = os.path.join(c.SOURCE_DIR, fname)
        client_name = c.CLIENT_MAP.get(fname, fname.split(' Payment')[0].split(' -')[0])
        xls = pd.ExcelFile(fpath)
        pt_sheet, md_sheet, _ = c.identify_sheets(xls)

        if pt_sheet:
            df_pt = pd.read_excel(xls, sheet_name=pt_sheet)
            pt_rows = c.normalize_pt_sheet(df_pt, client_name, fname, mapping_mgr=mapping_mgr)
            all_pt_rows.extend(pt_rows)

        if md_sheet:
            df_md = pd.read_excel(xls, sheet_name=md_sheet)
            md_rows = c.normalize_md_sheet(df_md, client_name, fname, mapping_mgr=mapping_mgr)
            all_md_rows.extend(md_rows)

    pt_df = pd.DataFrame(all_pt_rows)
    md_df = pd.DataFrame(all_md_rows)

    # Total pay target check
    total_pay = pt_df['Total pay'].sum()
    assert abs(total_pay - 4181751.00) < 0.01, f"Total pay sum {total_pay} != 4181751.00"

    # Row counts check
    assert len(pt_df) == 592, f"PT row count {len(pt_df)} != 592"
    assert len(md_df) == 2565, f"MD row count {len(md_df)} != 2565"
    assert pt_df['client'].nunique() == 25, f"PT client count {pt_df['client'].nunique()} != 25"


def test_find_column_exact_and_simplified():
    source_cols = ["S.No", "Name of Auditor/Assayer", "A/C Number", "Cancelled Visits"]

    # Exact / Simplified
    assert c.find_column(["s.no"], source_cols) == "S.No"
    assert c.find_column(["ac number", "a/c number"], source_cols) == "A/C Number"
    assert c.find_column(["name of auditor/assayer"], source_cols) == "Name of Auditor/Assayer"


def test_find_column_word_overlap_safety():
    """Verify single-token candidates like 'date' don't falsely match multi-token headers."""
    source_cols = ["Zone Location", "Audit Status", "Scheduled Date"]

    # Candidate "schedule date" should match "Scheduled Date"
    matched = c.find_column(["schedule date"], source_cols)
    assert matched == "Scheduled Date"


def test_content_map_building():
    df = pd.DataFrame({
        'col_pan': ['ABCDE1234F', 'FGHIJ5678K', 'KLMNO9012P'],
        'col_phone': ['9876543210', '9123456789', '9998887776'],
        'col_sol': ['1234', '5678', '9012'],
        'col_zone': ['North', 'South', 'West'],
    })
    cmap = c.build_content_map(df)
    assert cmap.get('pan') == 'col_pan'
    assert cmap.get('phone') == 'col_phone'
    assert cmap.get('sol_id') == 'col_sol'
    assert cmap.get('zone') == 'col_zone'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
