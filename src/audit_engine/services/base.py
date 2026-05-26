"""Abstract base service for bank-specific PDF generation.

All bank services implement this interface. The rest of the application
depends on this abstraction, not on concrete implementations.
"""

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable

from audit_engine.domain.models import GenerationResult, ValidationResult


class BankService(ABC):
    """Interface that every bank PDF generation service must implement."""

    @abstractmethod
    def validate(self, filepath: str) -> ValidationResult:
        """Validate that an Excel file matches this bank's expected format."""
        ...

    @abstractmethod
    def process(
        self,
        filepath: str,
        output_dir: str,
        log_func: Callable[[str, str], None],
        cancel_event: threading.Event,
        progress_callback: Callable[[float], None],
    ) -> GenerationResult:
        """Process a single Excel file and generate PDF outputs."""
        ...

    @abstractmethod
    def detect(self, filepath: str) -> bool:
        """Return True if the file appears to be from this bank."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable bank name."""
        ...
