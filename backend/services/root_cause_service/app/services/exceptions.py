import uuid

from backend.shared.constants.enums.root_cause import RootCauseStatus


class IncidentNotFoundError(Exception):
    """Raised when the Incident referenced by an operation does not exist."""

    def __init__(self, incident_id: uuid.UUID) -> None:
        self.incident_id = incident_id
        super().__init__(f"Incident {incident_id} not found")


class RootCauseAlreadyExistsError(Exception):
    """Raised when a RootCause already exists for the referenced Incident."""

    def __init__(self, incident_id: uuid.UUID) -> None:
        self.incident_id = incident_id
        super().__init__(f"RootCause already exists for incident {incident_id}")


class RootCauseNotFoundError(Exception):
    """Raised when the RootCause referenced by a lifecycle operation does not exist."""

    def __init__(self, root_cause_id: uuid.UUID) -> None:
        self.root_cause_id = root_cause_id
        super().__init__(f"RootCause {root_cause_id} not found")


class InvalidLifecycleTransitionError(Exception):
    """Raised when a confirm/reject operation would perform a disallowed status transition."""

    def __init__(self, current_status: RootCauseStatus, target_status: RootCauseStatus) -> None:
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(f"Cannot transition RootCause from {current_status.value} to {target_status.value}")


class RefreshNotAllowedError(Exception):
    """Raised when a refresh is attempted on a RootCause in a terminal state (CONFIRMED or REJECTED)."""

    def __init__(self, current_status: RootCauseStatus) -> None:
        self.current_status = current_status
        super().__init__(f"Cannot refresh a RootCause in terminal state {current_status.value}")
