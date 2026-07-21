from typing import Dict, Set

from backend.services.root_cause_service.app.services.exceptions import (
    InvalidLifecycleTransitionError,
    RefreshNotAllowedError,
)
from backend.shared.constants.enums.root_cause import RootCauseStatus

# Centralised, deterministic transition table. CONFIRMED->CONFIRMED and
# REJECTED->REJECTED are explicit no-op/idempotent entries (re-confirming or
# re-rejecting an already-terminal RootCause succeeds without changing
# anything). CONFIRMED<->REJECTED is never present in either direction.
_ALLOWED_TRANSITIONS: Dict[RootCauseStatus, Set[RootCauseStatus]] = {
    RootCauseStatus.IDENTIFIED: {RootCauseStatus.CONFIRMED, RootCauseStatus.REJECTED},
    RootCauseStatus.CONFIRMED: {RootCauseStatus.CONFIRMED},
    RootCauseStatus.REJECTED: {RootCauseStatus.REJECTED},
}

_TERMINAL_STATES: Set[RootCauseStatus] = {RootCauseStatus.CONFIRMED, RootCauseStatus.REJECTED}


class LifecycleValidator:
    """
    Lifecycle Validator

    Ownership:
    Owned by the Root Cause Service.

    Operational Purpose:
    Pure, stateless validation of RootCause lifecycle rules. Contains no
    persistence and no inference — only the deterministic transition and
    refresh rules the Application Service delegates to before mutating a
    RootCause.
    """

    @staticmethod
    def validate_transition(current_status: RootCauseStatus, target_status: RootCauseStatus) -> None:
        """
        Raises `InvalidLifecycleTransitionError` unless `current_status ->
        target_status` is an allowed confirm/reject transition.
        """
        allowed = _ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise InvalidLifecycleTransitionError(current_status, target_status)

    @staticmethod
    def validate_terminal_state(status: RootCauseStatus) -> None:
        """Raises `RefreshNotAllowedError` if `status` is a terminal state (CONFIRMED or REJECTED)."""
        if status in _TERMINAL_STATES:
            raise RefreshNotAllowedError(status)

    @staticmethod
    def validate_refresh(status: RootCauseStatus) -> None:
        """Refresh is allowed only while IDENTIFIED — delegates to `validate_terminal_state`."""
        LifecycleValidator.validate_terminal_state(status)
