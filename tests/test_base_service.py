"""Tests for the abstract BankService base class."""

from audit_engine.services.base import BankService


class TestBankServiceABC:
    def test_cannot_instantiate_abstract(self):
        """BankService has abstract methods and cannot be instantiated directly."""
        try:
            BankService()  # type: ignore[abstract]
            assert False, "Should have raised TypeError"
        except TypeError as e:
            assert "Can't instantiate abstract class" in str(e)

    def test_has_abstract_methods(self):
        abstract_methods = BankService.__abstractmethods__
        assert "validate" in abstract_methods
        assert "process" in abstract_methods
        assert "detect" in abstract_methods
        assert "name" in abstract_methods

    def test_name_is_property(self):
        assert isinstance(BankService.__dict__["name"], property)

    def test_validate_signature(self):
        import inspect
        sig = inspect.signature(BankService.validate)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "filepath" in params

    def test_process_signature(self):
        import inspect
        sig = inspect.signature(BankService.process)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "filepath" in params
        assert "output_dir" in params
        assert "log_func" in params
        assert "cancel_event" in params
        assert "progress_callback" in params
