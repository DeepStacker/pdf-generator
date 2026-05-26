"""Tests for domain enumerations."""

from audit_engine.domain.enums import AuditType, BankType, EquitasFormat, EquitasStage, LogLevel, OutputMode


def test_bank_type_values():
    assert BankType.IDFC.value == "IDFC First Bank"
    assert BankType.EQUITAS.value == "Equitas Small Finance Bank"
    assert BankType.ARVOG.value == "Arvog Bank"
    assert BankType.UNKNOWN.value == "Unknown"


def test_bank_type_membership():
    assert BankType.IDFC in BankType
    assert BankType.UNKNOWN in BankType


def test_output_mode_values():
    assert OutputMode.FOLDER.value == "FOLDER"
    assert OutputMode.ZIP_ONLY.value == "ZIP ONLY"
    assert OutputMode.BOTH.value == "BOTH"
    assert OutputMode.FOLDER != OutputMode.BOTH


def test_audit_type_values():
    assert AuditType.POA.value == "POA"
    assert AuditType.TAF.value == "TAF"


def test_equitas_format_values():
    assert EquitasFormat.PDF_ONLY.value == "PDF ONLY"
    assert EquitasFormat.EXCEL_ONLY.value == "EXCEL ONLY"
    assert EquitasFormat.BOTH.value == "BOTH"


def test_equitas_stage_values():
    assert EquitasStage.STAGE_1.value == "STAGE 1"
    assert EquitasStage.STAGE_2.value == "STAGE 2"


def test_log_level_values():
    assert LogLevel.INFO.value == "INFO"
    assert LogLevel.WARN.value == "WARN"
    assert LogLevel.ERROR.value == "ERROR"
    assert LogLevel.OK.value == "OK"
