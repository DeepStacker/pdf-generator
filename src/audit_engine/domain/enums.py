"""Domain enumerations."""

from enum import Enum, auto


class BankType(Enum):
    IDFC = "IDFC First Bank"
    EQUITAS = "Equitas Small Finance Bank"
    ARVOG = "Arvog Bank"
    UNKNOWN = "Unknown"


class OutputMode(Enum):
    FOLDER = auto()
    ZIP_ONLY = auto()
    BOTH = auto()


class EquitasStage(Enum):
    STAGE_1 = "STAGE 1"
    STAGE_2 = "STAGE 2"


class LogLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    OK = "OK"
