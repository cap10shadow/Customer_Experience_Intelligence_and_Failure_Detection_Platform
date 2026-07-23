from sqlalchemy import Column, Enum, Float, Integer, MetaData, String, Table
from sqlalchemy.dialects.postgresql import UUID

from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.root_cause import RootCause as RootCauseEnum

# Dedicated MetaData instance, intentionally separate from the shared
# declarative `Base` used by this service's own `BusinessImpactAssessmentEntity`.
# The Business Impact Service only ever reads `incidents`, `active_anomalies`,
# and `incident_anomalies` (owned by the Anomaly Service), plus `root_causes`
# (owned by the Root Cause Service) -- it must never import those services'
# ORM model classes to stay independently deployable (DATA-002). These Table
# objects are unmapped (no ORM entities, no relationships) and declare only
# the columns Business Impact analysis actually reads.
read_models_metadata = MetaData()

incidents_table = Table(
    "incidents",
    read_models_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("severity", Enum(AnomalySeverity)),
)

active_anomalies_table = Table(
    "active_anomalies",
    read_models_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("type", Enum(AnomalyType)),
    Column("entity_type", String(50)),
    Column("entity_value", String(255)),
    Column("baseline_value", Float),
    Column("current_value", Float),
    Column("percentage_change", Float),
)

incident_anomalies_table = Table(
    "incident_anomalies",
    read_models_metadata,
    Column("incident_id", UUID(as_uuid=True)),
    Column("active_anomaly_id", UUID(as_uuid=True)),
)

root_causes_table = Table(
    "root_causes",
    read_models_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("incident_id", UUID(as_uuid=True)),
    Column("cause", Enum(RootCauseEnum)),
    Column("confidence_score", Integer),
    Column("confidence_level", String(20)),
)
