from sqlalchemy import Column, Enum, Integer, MetaData, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID

from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.incident import IncidentStatus

# Dedicated MetaData instance, intentionally separate from the shared
# declarative `Base` used by other services. The Root Cause Service only
# ever reads `incidents`, `incident_anomalies`, and `active_anomalies` —
# tables owned by the Anomaly Service — and must never import that
# service's ORM model classes to stay independently deployable (DATA-002).
# These Table objects are unmapped (no ORM entities, no relationships) and
# declare only the columns Root Cause analysis actually reads.
read_models_metadata = MetaData()

incidents_table = Table(
    "incidents",
    read_models_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("incident_key", String(50)),
    Column("title", String(255)),
    Column("severity", Enum(AnomalySeverity)),
    Column("status", Enum(IncidentStatus)),
    Column("confidence_score", Integer),
    Column("summary", Text),
)

active_anomalies_table = Table(
    "active_anomalies",
    read_models_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("type", Enum(AnomalyType)),
    Column("entity_type", String(50)),
    Column("entity_value", String(255)),
)

incident_anomalies_table = Table(
    "incident_anomalies",
    read_models_metadata,
    Column("incident_id", UUID(as_uuid=True)),
    Column("active_anomaly_id", UUID(as_uuid=True)),
)
