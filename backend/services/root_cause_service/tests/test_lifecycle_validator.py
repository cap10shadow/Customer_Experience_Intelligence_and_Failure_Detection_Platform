import pytest

from backend.services.root_cause_service.app.services.exceptions import (
    InvalidLifecycleTransitionError,
    RefreshNotAllowedError,
)
from backend.services.root_cause_service.app.services.lifecycle_validator import LifecycleValidator
from backend.shared.constants.enums.root_cause import RootCauseStatus


def test_identified_to_confirmed_is_allowed():
    LifecycleValidator.validate_transition(RootCauseStatus.IDENTIFIED, RootCauseStatus.CONFIRMED)


def test_identified_to_rejected_is_allowed():
    LifecycleValidator.validate_transition(RootCauseStatus.IDENTIFIED, RootCauseStatus.REJECTED)


def test_confirmed_to_confirmed_is_idempotent_and_allowed():
    LifecycleValidator.validate_transition(RootCauseStatus.CONFIRMED, RootCauseStatus.CONFIRMED)


def test_rejected_to_rejected_is_idempotent_and_allowed():
    LifecycleValidator.validate_transition(RootCauseStatus.REJECTED, RootCauseStatus.REJECTED)


def test_confirmed_to_rejected_is_forbidden():
    with pytest.raises(InvalidLifecycleTransitionError) as exc_info:
        LifecycleValidator.validate_transition(RootCauseStatus.CONFIRMED, RootCauseStatus.REJECTED)
    assert exc_info.value.current_status == RootCauseStatus.CONFIRMED
    assert exc_info.value.target_status == RootCauseStatus.REJECTED


def test_rejected_to_confirmed_is_forbidden():
    with pytest.raises(InvalidLifecycleTransitionError) as exc_info:
        LifecycleValidator.validate_transition(RootCauseStatus.REJECTED, RootCauseStatus.CONFIRMED)
    assert exc_info.value.current_status == RootCauseStatus.REJECTED
    assert exc_info.value.target_status == RootCauseStatus.CONFIRMED


def test_identified_to_identified_is_not_a_defined_transition():
    # Confirm/reject never target IDENTIFIED, so this must not be allowed.
    with pytest.raises(InvalidLifecycleTransitionError):
        LifecycleValidator.validate_transition(RootCauseStatus.IDENTIFIED, RootCauseStatus.IDENTIFIED)


def test_validate_terminal_state_allows_identified():
    LifecycleValidator.validate_terminal_state(RootCauseStatus.IDENTIFIED)


def test_validate_terminal_state_rejects_confirmed():
    with pytest.raises(RefreshNotAllowedError) as exc_info:
        LifecycleValidator.validate_terminal_state(RootCauseStatus.CONFIRMED)
    assert exc_info.value.current_status == RootCauseStatus.CONFIRMED


def test_validate_terminal_state_rejects_rejected():
    with pytest.raises(RefreshNotAllowedError) as exc_info:
        LifecycleValidator.validate_terminal_state(RootCauseStatus.REJECTED)
    assert exc_info.value.current_status == RootCauseStatus.REJECTED


def test_validate_refresh_allows_identified():
    LifecycleValidator.validate_refresh(RootCauseStatus.IDENTIFIED)


def test_validate_refresh_rejects_confirmed():
    with pytest.raises(RefreshNotAllowedError):
        LifecycleValidator.validate_refresh(RootCauseStatus.CONFIRMED)


def test_validate_refresh_rejects_rejected():
    with pytest.raises(RefreshNotAllowedError):
        LifecycleValidator.validate_refresh(RootCauseStatus.REJECTED)
