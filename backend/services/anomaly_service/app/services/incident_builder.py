import uuid
from typing import List

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly
from backend.shared.constants.enums.anomaly import AnomalySeverity

# Ordinal ordering for picking the "worst" severity among a group of anomalies.
_SEVERITY_ORDER = [
    AnomalySeverity.NORMAL,
    AnomalySeverity.LOW,
    AnomalySeverity.MEDIUM,
    AnomalySeverity.HIGH,
    AnomalySeverity.CRITICAL,
]


def generate_incident_key() -> str:
    """A short, stable, human-referenceable identifier assigned once at creation."""
    return f"INC-{uuid.uuid4().hex[:8].upper()}"


def aggregate_severity(anomalies: List[ActiveAnomaly]) -> AnomalySeverity:
    """An incident's severity is the highest severity among its linked anomalies."""
    return max(anomalies, key=lambda a: _SEVERITY_ORDER.index(a.severity)).severity


def build_title(anomalies: List[ActiveAnomaly]) -> str:
    """
    Deterministically titles an incident from its anomalies' shared
    dimensions — no free-text generation, just rule-based labeling.
    """
    regions = {a.entity_value for a in anomalies if a.entity_type == "region" and a.entity_value}
    categories = {a.entity_value for a in anomalies if a.entity_type == "category" and a.entity_value}

    region = next(iter(regions)) if len(regions) == 1 else None
    category = next(iter(categories)) if len(categories) == 1 else None

    if region and category:
        return f"{region} — {category} Incident"
    if region:
        return f"{region} Regional Incident"
    if category:
        return f"{category} Category Incident"
    return f"Multi-Signal Incident ({len(anomalies)} anomalies)"
