import uuid


class IncidentNotFoundError(Exception):
    """Raised when the Incident referenced by an operation does not exist."""

    def __init__(self, incident_id: uuid.UUID) -> None:
        self.incident_id = incident_id
        super().__init__(f"Incident {incident_id} not found")


class RootCauseNotFoundError(Exception):
    """Raised when no RootCause has been identified yet for the referenced Incident."""

    def __init__(self, incident_id: uuid.UUID) -> None:
        self.incident_id = incident_id
        super().__init__(f"RootCause not found for incident {incident_id}")
