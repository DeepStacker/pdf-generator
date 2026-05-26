"""Tests for the exception hierarchy."""

from audit_engine.exceptions import (
    AuditEngineError,
    ConfigurationError,
    DatabaseError,
    DialogError,
    GenerationError,
    UpdateError,
    ValidationError,
)


def test_base_exception():
    assert issubclass(ConfigurationError, AuditEngineError)
    assert issubclass(DatabaseError, AuditEngineError)
    assert issubclass(ValidationError, AuditEngineError)
    assert issubclass(GenerationError, AuditEngineError)
    assert issubclass(UpdateError, AuditEngineError)
    assert issubclass(DialogError, AuditEngineError)


def test_exception_can_be_raised_and_caught():
    try:
        raise ValidationError("bad input")
    except AuditEngineError as e:
        assert str(e) == "bad input"


def test_exception_is_not_base():
    with_message = ConfigurationError("config missing")
    assert isinstance(with_message, AuditEngineError)
    assert str(with_message) == "config missing"
