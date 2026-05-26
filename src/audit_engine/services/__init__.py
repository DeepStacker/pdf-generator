"""Bank-specific PDF generation and audit logic services.

Each module provides:
- A class-based service with a clean API (e.g., IDFCService)
- Backward-compatible module-level functions for existing callers

New code should instantiate service classes directly.
"""

from audit_engine.services.arvog import ArvogService
from audit_engine.services.equitas import EquitasService
from audit_engine.services.idfc import IDFCService

__all__ = ["IDFCService", "EquitasService", "ArvogService"]
