"""Where each column sits in an Arvog sheet.

Two shapes are in circulation and both have to be read:

* the **wide master** a branch sends — loan columns, then one block per
  ornament spread sideways, then more loan columns;
* the **tall audit sheet** we produce from it — one row per ornament, with the
  auditor's hand-filled block closing each row.

Columns are located rather than assumed. The wide reader used to find
ornament *i* through the suffix pandas appends to duplicate headers
(``Gross Wt..1``, ``Karat.1``, …), which silently encodes "every ornament
occupies exactly seven columns". A rebuilt master carries fifteen, because the
auditor's block travels with each ornament and repeats ``Gross Wt.`` and
``Karat``; the suffixes then shift by two per block and ornament 2's weight is
read from ornament 1's audit cell. No error, just wrong numbers.

So the header row is read raw — before pandas renames anything — each ornament
is anchored on its own ``Jewellery{i}`` heading, and the columns in between are
matched by name. That reads both shapes, and makes the odd spelling of the
twentieth block's purity column a non-event.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Final

import openpyxl

logger = logging.getLogger(__name__)

# An Arvog master never carries more than twenty ornaments per loan.
MAX_ORNAMENTS: Final[int] = 20

# Loan-level columns, before and after the ornament blocks.
LEADING_COLUMNS: Final[list[str]] = [
    "SR No.", "Branch", "Region", "Date", "Customer Name", "Loan No.",
    "Loan type", "Partner Name", "Customer ID",
]
TRAILING_COLUMNS: Final[list[str]] = [
    "Loan Amount", "Auditor Name", "Appraiser Name", "Packets Location",
    "Cluster Manager", "Packets Number", "After audit packet number",
]

# The auditor's own tally, filled in by hand at the branch.
AUDIT_BLOCK_COLUMNS: Final[list[str]] = [
    "Count of Ornament", "Gross Wt.", "Stone Wt", "Karat", "Purity%",
    "Net Weight", "Remarks",
]
AUDIT_BANNER: Final[str] = "Sumeru"

# One ornament, as the tall sheet lays it out.
ORNAMENT_COLUMNS: Final[list[str]] = [
    "Jewellery No.", "Jewellery1", "Gross Wt.", "Stone Wt.", "Net Wt.",
    "Karat", "Purity % %", "Net weight after Purity %",
]

# What the branch records per ornament, keyed by normalised heading. The last
# block of a twenty-ornament master spells its purity column differently, which
# is why two headings map to the same attribute.
_DATA_ATTRS: Final[dict[str, str]] = {
    "gross wt.": "gross",
    "stone wt.": "stone",
    "net wt.": "net",
    "karat": "karat",
    "purity % %": "purity",
    "net weight after purity %": "net_after_purity",
    "final net weight after purity %": "net_after_purity",
}

# Ordered attribute keys, matching ORNAMENT_COLUMNS after the two name columns.
DATA_ATTR_ORDER: Final[list[str]] = [
    "gross", "stone", "net", "karat", "purity", "net_after_purity",
]

_ANCHOR_RE: Final[re.Pattern[str]] = re.compile(r"^jewellery\s*(\d+)$")
_JEWELLERY_NO: Final[str] = "jewellery no."
_AUDIT_SPLIT: Final[str] = "count of ornament"

# How far down a sheet to look for the header row. Ours is on row 1 or 2
# depending on whether the file predates the "Sumeru" banner; hand-edited files
# occasionally carry a title above it.
HEADER_SCAN_ROWS: Final[int] = 10


def normalize_header(value: Any) -> str:
    """Lower-case, trimmed, with runs of whitespace collapsed.

    These sheets are hand-edited, so a heading may arrive padded, wrapped over
    two lines, or in a different case than the template.
    """
    if value is None:
        return ""
    return " ".join(str(value).split()).lower()


def read_rows(excel_path: str, sheet_name: str, limit: int) -> list[list[Any]]:
    """Read the first `limit` rows of a sheet, values only."""
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    try:
        ws = wb[sheet_name]
        return [list(row) for row in ws.iter_rows(max_row=limit, values_only=True)]
    finally:
        wb.close()


def read_header_row(excel_path: str, sheet_name: str, header_row: int) -> list[str]:
    """The header row exactly as the file has it, before pandas renames anything.

    `header_row` is 0-based, matching what `detect_raw_excel` returns and what
    `pandas.read_excel(header=...)` expects.
    """
    rows = read_rows(excel_path, sheet_name, header_row + 1)
    if len(rows) <= header_row:
        return []
    return ["" if v is None else str(v).strip() for v in rows[header_row]]


def find_header_row(rows: list[list[Any]], required: list[str]) -> int | None:
    """Index of the first row carrying all of `required`, or None.

    Used instead of assuming row 0: a sheet we produce now has the "Sumeru"
    banner above its headings, and sheets produced before that banner existed
    do not.
    """
    wanted = {normalize_header(r) for r in required}
    for index, row in enumerate(rows):
        present = {normalize_header(v) for v in row if v is not None}
        if wanted <= present:
            return index
    return None


@dataclass(frozen=True)
class OrnamentColumns:
    """Absolute 0-based column indexes for one ornament block."""

    number: int
    name: int
    data: dict[str, int] = field(default_factory=dict)
    audit: dict[str, int] = field(default_factory=dict)

    @property
    def has_audit_block(self) -> bool:
        return bool(self.audit)


def map_ornaments(headers: list[Any]) -> list[OrnamentColumns]:
    """Locate every ornament block in a wide header row.

    Each block is anchored on its own ``Jewellery{i}`` heading and runs to the
    next anchor. Within a block, ``Count of Ornament`` marks where the branch's
    figures end and the auditor's begin — the two halves repeat ``Gross Wt.``
    and ``Karat``, so the split is what keeps them apart.
    """
    normalized = [normalize_header(h) for h in headers]

    anchors: list[tuple[int, int]] = []  # (column index, ornament number)
    for index, header in enumerate(normalized):
        match = _ANCHOR_RE.match(header)
        if match:
            anchors.append((index, int(match.group(1))))

    blocks: list[OrnamentColumns] = []
    for position, (index, number) in enumerate(anchors):
        end = anchors[position + 1][0] if position + 1 < len(anchors) else len(normalized)
        # "Jewellery No." belongs to the block that follows it, so it sits at
        # the tail of this span. Skipping it costs nothing — the value is
        # derived from the ornament number, never read.
        span = [
            (i, normalized[i]) for i in range(index + 1, end)
            if normalized[i] and normalized[i] != _JEWELLERY_NO
        ]

        split = next((n for n, (_, h) in enumerate(span) if h == _AUDIT_SPLIT), len(span))
        data_part, audit_part = span[:split], span[split:]

        data = {}
        for column, header in data_part:
            attribute = _DATA_ATTRS.get(header)
            if attribute and attribute not in data:
                data[attribute] = column

        audit = {}
        for heading in AUDIT_BLOCK_COLUMNS:
            key = normalize_header(heading)
            for column, header in audit_part:
                if header == key and heading not in audit:
                    audit[heading] = column
                    break

        blocks.append(OrnamentColumns(number=number, name=index, data=data, audit=audit))

    over_cap = [b for b in blocks if b.number > MAX_ORNAMENTS]
    if over_cap:
        logger.warning(
            "Sheet declares ornaments beyond %d (%s); they will be ignored",
            MAX_ORNAMENTS, ", ".join(str(b.number) for b in over_cap),
        )
        blocks = [b for b in blocks if b.number <= MAX_ORNAMENTS]

    return blocks


def index_of(headers: list[Any], heading: str, start: int = 0) -> int | None:
    """First column at or after `start` whose heading matches, or None."""
    key = normalize_header(heading)
    for index in range(start, len(headers)):
        if normalize_header(headers[index]) == key:
            return index
    return None
