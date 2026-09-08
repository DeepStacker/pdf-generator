"""Column type registry for Arvog master sheets.

Arvog files arrive from branch staff with the same column meaning spelled a
dozen ways: a loan number read back as ``123456.0``, a weight as ``2`` in one
row and ``2.500`` in the next, purity as ``0.916`` in one file and ``91.6`` in
another, a date as text. Formatting each column at the point of use meant the
Excel and the PDF could disagree about the same cell.

So the type of a column is declared once, here, and everything downstream —
value cleaning, the Excel number format, the PDF cell text — is derived from
that single declaration.

Normalisation never rounds a stored value. Weights and amounts keep the
precision the branch entered; the fixed decimals are a *display* decision,
applied by the Excel number format and by :func:`display_value` for the PDF.
Nor does it discard anything it cannot parse: an unparseable cell keeps its
original text rather than silently becoming blank, because a blank in an audit
report reads as "nothing was there".
"""

import logging
import re
from enum import Enum
from typing import Any, Final

import pandas as pd

logger = logging.getLogger(__name__)

# Weights and money are shown to two decimals, matching the number format the
# Arvog workbook has always used. Underlying values keep full precision.
WEIGHT_DECIMALS: Final[int] = 2
MONEY_DECIMALS: Final[int] = 2
PERCENT_DECIMALS: Final[int] = 2

# pandas reads a numeric ID column as float, so "123456" comes back "123456.0".
_TRAILING_ZERO_DECIMALS_RE: Final[re.Pattern[str]] = re.compile(r"-?\d+\.0+")

# Above this, a purity column is storing whole percents (91.6) rather than a
# fraction (0.916). Purity never legitimately exceeds 1.0 as a fraction, so the
# gap between the two conventions is wide and unambiguous.
_PERCENT_AS_FRACTION_CEILING: Final[float] = 1.5

# Dividing whole percents by 100 leaves binary-float noise (91.6 / 100 becomes
# 0.9159999999999999). Six places is far beyond the two that are displayed, so
# this clears the artefact without touching real precision.
_PERCENT_STORED_PLACES: Final[int] = 6


class ColumnKind(Enum):
    """What a column *is*, independent of how any one file happens to store it."""

    TEXT = "text"
    IDENTIFIER = "identifier"  # codes that look numeric but are labels: loan no, packet no
    INTEGER = "integer"
    WEIGHT = "weight"
    KARAT = "karat"  # numeric on most sheets ("22"), lettered on some ("22K")
    PERCENT = "percent"
    MONEY = "money"
    DATE = "date"


# Declared per column, keyed by the header lower-cased and trimmed. A header
# that is not listed is left exactly as the file had it — unknown columns are
# passed through untouched rather than guessed at.
COLUMN_KINDS: Final[dict[str, ColumnKind]] = {
    "sr no.": ColumnKind.INTEGER,
    "branch": ColumnKind.TEXT,
    "region": ColumnKind.TEXT,
    "date": ColumnKind.DATE,
    "customer name": ColumnKind.TEXT,
    "loan no.": ColumnKind.IDENTIFIER,
    "loan type": ColumnKind.TEXT,
    "partner name": ColumnKind.TEXT,
    "customer id": ColumnKind.IDENTIFIER,
    "jewellery no.": ColumnKind.IDENTIFIER,
    "jewellery1": ColumnKind.TEXT,
    "gross wt.": ColumnKind.WEIGHT,
    "stone wt.": ColumnKind.WEIGHT,
    "net wt.": ColumnKind.WEIGHT,
    "karat": ColumnKind.KARAT,
    "purity % %": ColumnKind.PERCENT,
    "net weight after purity %": ColumnKind.WEIGHT,
    "final net weight after purity %": ColumnKind.WEIGHT,
    "loan amount": ColumnKind.MONEY,
    "auditor name": ColumnKind.TEXT,
    "appraiser name": ColumnKind.TEXT,
    "packets location": ColumnKind.TEXT,
    "cluster manager": ColumnKind.TEXT,
    "packets number": ColumnKind.IDENTIFIER,
    # A packet number, not a date — it used to carry a d-mmm-yy number format,
    # which turned "45" into a day in February.
    "after audit packet number": ColumnKind.IDENTIFIER,
    # The auditor's hand-filled block that closes the sheet. Written blank, but
    # typed so that whatever the auditor enters is displayed like the matching
    # column on the left. The spellings differ from their counterparts above
    # ("Stone Wt" without the period, "Purity%") because that is how the
    # report's own heading row reads.
    "count of ornament": ColumnKind.INTEGER,
    "stone wt": ColumnKind.WEIGHT,
    "net weight": ColumnKind.WEIGHT,
    "purity%": ColumnKind.PERCENT,
    "remarks": ColumnKind.TEXT,
}

# Excel number formats, one per kind. IDENTIFIER and TEXT take "@" so Excel
# stops helpfully reinterpreting a long loan number as 1.23457E+14.
_EXCEL_FORMATS: Final[dict[ColumnKind, str]] = {
    ColumnKind.TEXT: "@",
    ColumnKind.IDENTIFIER: "@",
    ColumnKind.INTEGER: "0",
    ColumnKind.WEIGHT: f"0.{'0' * WEIGHT_DECIMALS}",
    ColumnKind.KARAT: "0",
    ColumnKind.PERCENT: f"0.{'0' * PERCENT_DECIMALS}%",
    ColumnKind.MONEY: f"#,##0.{'0' * MONEY_DECIMALS}",
    ColumnKind.DATE: "dd-mmm-yy",
}

# Kinds that are numeric in principle but text in practice on some sheets. For
# these the format is chosen per column, from what the column actually holds.
_NUMERIC_OR_TEXT_KINDS: Final[frozenset[ColumnKind]] = frozenset({ColumnKind.INTEGER, ColumnKind.KARAT})

_GENERAL_FORMAT: Final[str] = "General"


def kind_for(header: Any) -> ColumnKind | None:
    """Return the declared kind for a column header, or None if undeclared."""
    if header is None:
        return None
    return COLUMN_KINDS.get(str(header).strip().lower())


def is_blank(value: Any) -> bool:
    """True for None, NaN/NaT, and whitespace-only strings."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        # pd.isna on a list/array returns an array, which will not reduce to a
        # bool. A container is not blank.
        return False


# ---------------------------------------------------------------------------
# Scalar normalisers — clean the value, never round it, never drop it
# ---------------------------------------------------------------------------

def _to_number(value: Any) -> float | None:
    """Parse a cell to a float, tolerating thousands separators. None if not numeric."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def normalize_text(value: Any) -> str | None:
    """Trim, collapse runs of whitespace, and turn an empty result into None."""
    if is_blank(value):
        return None
    return " ".join(str(value).split()) or None


def normalize_identifier(value: Any) -> str | None:
    """Keep a code as text, without the ".0" a numeric read tacks on."""
    if is_blank(value):
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if float(value).is_integer() else f"{value:g}"
    text = " ".join(str(value).split())
    if _TRAILING_ZERO_DECIMALS_RE.fullmatch(text):
        text = text.split(".", 1)[0]
    return text or None


def normalize_integer(value: Any) -> int | float | str | None:
    """Whole numbers become ints; anything else is kept as it was."""
    if is_blank(value):
        return None
    if isinstance(value, bool):
        return int(value)
    number = _to_number(value)
    if number is None:
        return normalize_text(value)
    return int(number) if number.is_integer() else number


def normalize_weight(value: Any) -> float | str | None:
    """Weights become floats at full precision; decimals are a display concern."""
    if is_blank(value):
        return None
    number = _to_number(value)
    return normalize_text(value) if number is None else number


def normalize_money(value: Any) -> float | str | None:
    if is_blank(value):
        return None
    number = _to_number(value)
    return normalize_text(value) if number is None else number


def normalize_karat(value: Any) -> int | float | str | None:
    """22.0 and " 22 " both become 22; "22k" becomes "22K"."""
    if is_blank(value):
        return None
    number = _to_number(value)
    if number is not None:
        return int(number) if number.is_integer() else number
    text = normalize_text(value)
    return text.upper() if text else None


_SCALAR_NORMALIZERS: Final[dict[ColumnKind, Any]] = {
    ColumnKind.TEXT: normalize_text,
    ColumnKind.IDENTIFIER: normalize_identifier,
    ColumnKind.INTEGER: normalize_integer,
    ColumnKind.WEIGHT: normalize_weight,
    ColumnKind.MONEY: normalize_money,
    ColumnKind.KARAT: normalize_karat,
}


# ---------------------------------------------------------------------------
# Column-wide normalisers — these need to see the whole column to decide
# ---------------------------------------------------------------------------

def normalize_percent_series(series: pd.Series) -> pd.Series:
    """Bring purity onto one scale: a fraction, so "0.00%" always renders right.

    Branches send purity either as 0.916 or as 91.6. Left alone, the same
    number format shows one of them as 92% and the other as 9160%. Whether a
    column uses whole percents is a property of the column, not of a cell, so
    the decision is made once from the column's maximum.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().any() and float(numeric.abs().max()) > _PERCENT_AS_FRACTION_CEILING:
        numeric = (numeric / 100.0).round(_PERCENT_STORED_PLACES)
    # Keep the original text wherever the value was not a number at all.
    return numeric.where(numeric.notna(), series.map(normalize_text))


def normalize_date_series(series: pd.Series) -> pd.Series:
    """Parse dates day-first, keeping unparseable cells as their original text."""
    if pd.api.types.is_numeric_dtype(series):
        # Bare numbers here are Excel serials, and to_datetime would read them
        # as nanoseconds since the epoch. Leave them to the number format.
        return series
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
    if parsed.notna().all():
        return parsed
    return parsed.where(parsed.notna(), series.map(normalize_text))


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply each column's declared type. Idempotent — safe to call twice."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    seen: set[str] = set()
    for column in df.columns:
        if column in seen:
            # Two columns of the same name would make df[column] a DataFrame.
            logger.warning("Duplicate column %r left un-normalised", column)
            continue
        seen.add(column)

        kind = kind_for(column)
        if kind is None:
            continue
        if kind is ColumnKind.PERCENT:
            df[column] = normalize_percent_series(df[column])
        elif kind is ColumnKind.DATE:
            df[column] = normalize_date_series(df[column])
        else:
            df[column] = df[column].map(_SCALAR_NORMALIZERS[kind])

    return df


# ---------------------------------------------------------------------------
# Presentation — the Excel number format and the PDF cell text, same source
# ---------------------------------------------------------------------------

def format_depends_on_values(kind: ColumnKind | None) -> bool:
    """True when excel_format_for needs to see the column to decide."""
    return kind in _NUMERIC_OR_TEXT_KINDS


def excel_format_for(kind: ColumnKind | None, values: Any = ()) -> str:
    """Return the Excel number format for a column of this kind.

    ``values`` lets the numeric-or-text kinds pick a format from what the
    column actually holds, so a "22K" karat column is not formatted as a number.
    """
    if kind is None:
        return _GENERAL_FORMAT
    if kind in _NUMERIC_OR_TEXT_KINDS:
        populated = [v for v in values if not is_blank(v)]
        if populated and not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in populated):
            return _EXCEL_FORMATS[ColumnKind.TEXT]
    return _EXCEL_FORMATS[kind]


def display_value(value: Any, kind: ColumnKind | None = None) -> str:
    """Render a normalised value as the string the PDF should show.

    Matches what the Excel number format displays for the same cell, so the two
    outputs of a single run never disagree.
    """
    if is_blank(value):
        return ""

    if kind is ColumnKind.WEIGHT:
        number = _to_number(value)
        if number is not None:
            return f"{number:.{WEIGHT_DECIMALS}f}"
    elif kind is ColumnKind.MONEY:
        number = _to_number(value)
        if number is not None:
            return f"{number:,.{MONEY_DECIMALS}f}"
    elif kind is ColumnKind.PERCENT:
        number = _to_number(value)
        if number is not None:
            return f"{number * 100:.{PERCENT_DECIMALS}f}%"
    elif kind is ColumnKind.DATE:
        if isinstance(value, pd.Timestamp) or hasattr(value, "strftime"):
            return value.strftime("%d-%b-%y")
    elif kind is ColumnKind.INTEGER:
        number = _to_number(value)
        if number is not None and number.is_integer():
            return str(int(number))

    # Everything else, and every value that did not parse as its declared kind,
    # falls through to the general rendering below.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(int(value)) if float(value).is_integer() else str(value)

    text = str(value).strip()
    if _TRAILING_ZERO_DECIMALS_RE.fullmatch(text):
        return text.split(".", 1)[0]
    return text
