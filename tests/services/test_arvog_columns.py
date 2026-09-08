"""Tests for the Arvog column type registry and normalisation."""

import datetime as dt

import pandas as pd
import pytest

from audit_engine.services.arvog_columns import (
    ColumnKind,
    display_value,
    excel_format_for,
    is_blank,
    kind_for,
    normalize_dataframe,
    normalize_date_series,
    normalize_identifier,
    normalize_integer,
    normalize_karat,
    normalize_percent_series,
    normalize_text,
    normalize_weight,
)


class TestKindLookup:
    def test_known_headers_resolve(self):
        assert kind_for("Gross Wt.") is ColumnKind.WEIGHT
        assert kind_for("Loan No.") is ColumnKind.IDENTIFIER
        assert kind_for("Customer Name") is ColumnKind.TEXT
        assert kind_for("Purity % %") is ColumnKind.PERCENT
        assert kind_for("Loan Amount") is ColumnKind.MONEY
        assert kind_for("Date") is ColumnKind.DATE

    def test_lookup_ignores_case_and_padding(self):
        assert kind_for("  GROSS WT.  ") is ColumnKind.WEIGHT

    def test_unknown_header_is_left_alone(self):
        assert kind_for("Some New Column") is None
        assert kind_for(None) is None

    def test_after_audit_packet_number_is_an_identifier_not_a_date(self):
        """It used to carry a d-mmm-yy format, turning packet 45 into a date."""
        assert kind_for("After audit packet number") is ColumnKind.IDENTIFIER
        assert excel_format_for(ColumnKind.IDENTIFIER) == "@"


class TestIsBlank:
    @pytest.mark.parametrize("value", [None, "", "   ", float("nan"), pd.NA, pd.NaT])
    def test_blank_values(self, value):
        assert is_blank(value) is True

    @pytest.mark.parametrize("value", [0, 0.0, "0", "x", False])
    def test_non_blank_values(self, value):
        assert is_blank(value) is False

    def test_container_is_not_blank(self):
        assert is_blank([1, 2]) is False


class TestScalarNormalisers:
    def test_text_collapses_whitespace(self):
        assert normalize_text("  Ravi   Kumar \n") == "Ravi Kumar"
        assert normalize_text("   ") is None
        assert normalize_text(None) is None

    def test_identifier_drops_the_float_read_suffix(self):
        assert normalize_identifier(123456.0) == "123456"
        assert normalize_identifier("123456.0") == "123456"
        assert normalize_identifier("123456.00") == "123456"
        assert normalize_identifier(123456) == "123456"
        assert normalize_identifier(" LN-99 ") == "LN-99"
        assert normalize_identifier(None) is None

    def test_identifier_keeps_a_long_number_exact(self):
        assert normalize_identifier(123456789012345.0) == "123456789012345"

    def test_integer_only_converts_whole_numbers(self):
        assert normalize_integer("7") == 7
        assert normalize_integer(7.0) == 7
        assert normalize_integer(7.5) == 7.5
        assert normalize_integer("N/A") == "N/A"
        assert normalize_integer(None) is None

    def test_weight_keeps_full_precision(self):
        """Rounding here would lose audit data; decimals are a display choice."""
        assert normalize_weight("12.345") == 12.345
        assert normalize_weight(2) == 2.0
        assert normalize_weight("1,024.5") == 1024.5

    def test_weight_keeps_unparseable_text_rather_than_blanking_it(self):
        assert normalize_weight("NOT WEIGHED") == "NOT WEIGHED"
        assert normalize_weight("") is None

    def test_karat_handles_both_conventions(self):
        assert normalize_karat(22.0) == 22
        assert normalize_karat(" 22 ") == 22
        assert normalize_karat("22k") == "22K"
        assert normalize_karat(None) is None


class TestPercentSeries:
    def test_whole_percents_become_fractions(self):
        out = normalize_percent_series(pd.Series([91.6, 75.0]))
        assert out.tolist() == pytest.approx([0.916, 0.75])

    def test_fractions_are_left_alone(self):
        out = normalize_percent_series(pd.Series([0.916, 0.75]))
        assert out.tolist() == pytest.approx([0.916, 0.75])

    def test_scale_is_decided_per_column_not_per_cell(self):
        """A column with any whole-percent value is a whole-percent column."""
        out = normalize_percent_series(pd.Series([91.6, 0.5]))
        assert out.tolist() == pytest.approx([0.916, 0.005])

    def test_empty_column_survives(self):
        out = normalize_percent_series(pd.Series([None, None], dtype="object"))
        assert out.isna().all()


class TestDateSeries:
    def test_day_first_parsing(self):
        out = normalize_date_series(pd.Series(["05/03/2026"]))
        assert out.iloc[0] == pd.Timestamp("2026-03-05")

    def test_numeric_serials_are_left_for_the_number_format(self):
        serials = pd.Series([45000, 45001])
        assert normalize_date_series(serials).tolist() == [45000, 45001]

    def test_unparseable_text_is_kept(self):
        out = normalize_date_series(pd.Series(["05/03/2026", "not a date"]))
        assert out.iloc[0] == pd.Timestamp("2026-03-05")
        assert out.iloc[1] == "not a date"


class TestNormalizeDataFrame:
    def _frame(self):
        return pd.DataFrame({
            "SR No.": [1.0, 2.0],
            "Customer Name": ["  Ravi   Kumar ", "Sita"],
            "Loan No.": [123456.0, 123457.0],
            "Gross Wt.": ["12.345", 2],
            "Karat": [22.0, "22k"],
            "Purity % %": [91.6, 75.0],
            "Unlisted Column": ["as-is  ", "  keep"],
        })

    def test_each_column_follows_its_declared_type(self):
        out = normalize_dataframe(self._frame())
        assert out["SR No."].tolist() == [1, 2]
        assert out["Customer Name"].tolist() == ["Ravi Kumar", "Sita"]
        assert out["Loan No."].tolist() == ["123456", "123457"]
        assert out["Gross Wt."].tolist() == [12.345, 2.0]
        assert out["Karat"].tolist() == [22, "22K"]
        assert out["Purity % %"].tolist() == pytest.approx([0.916, 0.75])

    def test_undeclared_columns_are_passed_through_untouched(self):
        out = normalize_dataframe(self._frame())
        assert out["Unlisted Column"].tolist() == ["as-is  ", "  keep"]

    def test_is_idempotent(self):
        once = normalize_dataframe(self._frame())
        twice = normalize_dataframe(once)
        pd.testing.assert_frame_equal(once, twice)

    def test_input_frame_is_not_mutated(self):
        df = self._frame()
        normalize_dataframe(df)
        assert df["Customer Name"].iloc[0] == "  Ravi   Kumar "

    def test_duplicate_column_names_do_not_crash(self):
        df = pd.DataFrame([[1, 2]], columns=["Gross Wt.", "Gross Wt."])
        assert normalize_dataframe(df) is not None


class TestExcelFormats:
    def test_text_columns_are_text_not_integers(self):
        """Every text column used to be given the integer format "0"."""
        assert excel_format_for(ColumnKind.TEXT) == "@"
        assert excel_format_for(ColumnKind.IDENTIFIER) == "@"

    def test_numeric_kinds(self):
        assert excel_format_for(ColumnKind.WEIGHT) == "0.00"
        assert excel_format_for(ColumnKind.MONEY) == "#,##0.00"
        assert excel_format_for(ColumnKind.DATE) == "dd-mmm-yy"

    def test_percent_keeps_two_decimals(self):
        """"0%" rounded 91.6% to 92% and lost the purity."""
        assert excel_format_for(ColumnKind.PERCENT) == "0.00%"

    def test_karat_format_follows_the_column_contents(self):
        assert excel_format_for(ColumnKind.KARAT, [22, 18]) == "0"
        assert excel_format_for(ColumnKind.KARAT, [22, "22K"]) == "@"
        assert excel_format_for(ColumnKind.KARAT, [None, None]) == "0"

    def test_undeclared_column_stays_general(self):
        assert excel_format_for(None) == "General"


class TestDisplayValue:
    def test_weights_are_consistent_regardless_of_how_they_were_stored(self):
        assert display_value(2, ColumnKind.WEIGHT) == "2.00"
        assert display_value(2.0, ColumnKind.WEIGHT) == "2.00"
        assert display_value("2.000", ColumnKind.WEIGHT) == "2.00"
        assert display_value(2.5, ColumnKind.WEIGHT) == "2.50"

    def test_money_is_grouped(self):
        assert display_value(125000, ColumnKind.MONEY) == "125,000.00"

    def test_percent_matches_the_excel_number_format(self):
        assert display_value(0.916, ColumnKind.PERCENT) == "91.60%"

    def test_dates(self):
        assert display_value(dt.datetime(2026, 3, 5), ColumnKind.DATE) == "05-Mar-26"

    def test_identifier_keeps_its_digits(self):
        assert display_value("123456", ColumnKind.IDENTIFIER) == "123456"
        assert display_value(123456.0, ColumnKind.IDENTIFIER) == "123456"

    def test_blank_renders_empty(self):
        assert display_value(None, ColumnKind.WEIGHT) == ""
        assert display_value(pd.NA, ColumnKind.TEXT) == ""

    def test_unparseable_value_falls_back_to_its_text(self):
        assert display_value("NOT WEIGHED", ColumnKind.WEIGHT) == "NOT WEIGHED"

    def test_without_a_kind_it_behaves_as_before(self):
        assert display_value(5.0) == "5"
        assert display_value(5.5) == "5.5"
        assert display_value("3.0") == "3"
        assert display_value("hello") == "hello"
