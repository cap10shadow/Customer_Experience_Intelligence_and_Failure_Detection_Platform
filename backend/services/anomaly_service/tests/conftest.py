import uuid
from datetime import datetime, timezone

import pytest

from backend.services.anomaly_service.app.models.anomaly import ActiveAnomaly
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyStatus, AnomalyType


def _make_anomaly(
    *,
    type=AnomalyType.COMPLAINT_SPIKE,
    entity_type="global",
    entity_value=None,
    severity=AnomalySeverity.HIGH,
    first_detected_at=None,
    status=AnomalyStatus.ACTIVE,
    baseline_value=10.0,
    current_value=30.0,
    percentage_change=200.0,
) -> ActiveAnomaly:
    """Builds a plain (unpersisted) ActiveAnomaly for rule/engine unit tests."""
    timestamp = first_detected_at or datetime.now(timezone.utc)
    return ActiveAnomaly(
        id=uuid.uuid4(),
        fingerprint=f"{type.value}:{entity_type}:{entity_value or 'ALL'}",
        type=type,
        severity=severity,
        entity_type=entity_type,
        entity_value=entity_value,
        baseline_value=baseline_value,
        current_value=current_value,
        percentage_change=percentage_change,
        triggered_rule="test_rule",
        explanation="test explanation",
        first_detected_at=timestamp,
        last_seen_at=timestamp,
        status=status,
    )


@pytest.fixture
def make_anomaly():
    return _make_anomaly


@pytest.fixture
def anyio_backend():
    return "asyncio"
