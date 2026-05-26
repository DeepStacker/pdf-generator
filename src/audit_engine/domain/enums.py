"""Domain enumerations."""

from enum import Enum


class BankType(Enum):
    IDFC = "IDFC First Bank"
    EQUITAS = "Equitas Small Finance Bank"
    ARVOG = "Arvog Bank"
    UNKNOWN = "Unknown"


class AuditType(Enum):
    POA = "POA"
    TAF = "TAF"


class OutputMode(Enum):
    FOLDER = "FOLDER"
    ZIP_ONLY = "ZIP ONLY"
    BOTH = "BOTH"


class EquitasStage(Enum):
    STAGE_1 = "STAGE 1"
    STAGE_2 = "STAGE 2"


class EquitasFormat(Enum):
    PDF_ONLY = "PDF ONLY"
    EXCEL_ONLY = "EXCEL ONLY"
    BOTH = "BOTH"


class LogLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    OK = "OK"
