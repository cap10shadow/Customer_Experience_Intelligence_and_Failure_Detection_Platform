import uuid


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
