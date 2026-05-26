"""Tests for domain enumerations."""

from audit_engine.domain.enums import BankType, EquitasStage, LogLevel, OutputMode


def test_bank_type_values():
    assert BankType.IDFC.value == "IDFC First Bank"
    assert BankType.EQUITAS.value == "Equitas Small Finance Bank"
    assert BankType.ARVOG.value == "Arvog Bank"
    assert BankType.UNKNOWN.value == "Unknown"


def test_bank_type_membership():
    assert BankType.IDFC in BankType
    assert BankType.UNKNOWN in BankType


def test_output_mode_auto_values():
    assert isinstance(OutputMode.FOLDER.value, int)
    assert isinstance(OutputMode.ZIP_ONLY.value, int)
    assert isinstance(OutputMode.BOTH.value, int)
    assert OutputMode.FOLDER != OutputMode.BOTH


def test_equitas_stage_values():
    assert EquitasStage.STAGE_1.value == "STAGE 1"
    assert EquitasStage.STAGE_2.value == "STAGE 2"


def test_log_level_values():
    assert LogLevel.INFO.value == "INFO"
    assert LogLevel.WARN.value == "WARN"
    assert LogLevel.ERROR.value == "ERROR"
    assert LogLevel.OK.value == "OK"
