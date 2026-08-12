import asyncio
import time
import uuid

import httpx
import pytest

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.models.business_impact_assessment import (
    BusinessImpactAssessmentEntity,
)
from backend.services.business_impact_service.app.repositories.root_cause_read_repository import PersistedRootCause
from backend.services.business_impact_service.app.services.business_impact_event_publisher import (
    BusinessImpactCompletedEvent,
    BusinessImpactEventPublisher,
    build_evaluation_payload,
    build_recommendation_payload,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.business_impact_assessment import BusinessImpactAssessmentStatus
from backend.shared.constants.enums.root_cause import RootCause


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _event(**overrides) -> BusinessImpactCompletedEvent:
    incident_id = overrides.pop("incident_id", uuid.uuid4())
    assessment = BusinessImpactAssessmentEntity(
        assessment_id=uuid.uuid4(),
        incident_id=incident_id,
        root_cause_id=uuid.uuid4(),
        financial=ImpactLevel.HIGH,
        customer=ImpactLevel.MEDIUM,
        operational=ImpactLevel.CRITICAL,
        sla=ImpactLevel.LOW,
        reputation=ImpactLevel.NONE,
        overall_score=78,
        overall_severity=ImpactLevel.HIGH,
        business_priority=BusinessPriority.HIGH,
        confidence=80,
        estimated_affected_customers=250,
        explanation="Overall business impact is high.",
        status=BusinessImpactAssessmentStatus.ACTIVE,
    )
    root_cause = PersistedRootCause(
        id=uuid.uuid4(),
        incident_id=incident_id,
        cause=RootCause.SERVICE_OUTAGE,
        confidence_score=85,
        confidence_level="High",
        evidence=[{"source": "anomaly", "description": "spike"}],
        explanation="service_outage identified with critical anomaly severity",
    )
    defaults = dict(
        event_id=uuid.uuid4(),
        incident_id=incident_id,
        incident_severity=AnomalySeverity.CRITICAL,
        assessment=assessment,
        root_cause=root_cause,
    )
    defaults.update(overrides)
    return BusinessImpactCompletedEvent(**defaults)


class _RecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler):
        self._handler = handler

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await self._handler(request)


def _publisher(handler, *, timeout=1.0) -> BusinessImpactEventPublisher:
    client = httpx.AsyncClient(transport=_RecordingTransport(handler))
    return BusinessImpactEventPublisher(
        client,
        recommendation_url="http://recommendation_service:8006",
        evaluation_url="http://evaluation_service:8008",
        timeout_seconds=timeout,
    )


# ---------------------------------------------------------------------------
# Payload shape / event_id / incident_id semantics
# ---------------------------------------------------------------------------


def test_recommendation_payload_shape():
    event = _event()
    payload = build_recommendation_payload(event)

    assert payload["event_id"] == str(event.event_id)
    assert payload["incident"]["incident_id"] == str(event.incident_id)
    assert payload["incident"]["severity"] == "critical"
    assert payload["business_impact"]["business_score"] == 78
    assert payload["business_impact"]["overall_severity"] == "high"
    assert payload["root_cause"]["cause"] == "service_outage"
    assert payload["root_cause"]["confidence_score"] == 85
    assert "nlp_intelligence" not in payload
    assert "anomaly_intelligence" not in payload


def test_evaluation_payload_shape():
    event = _event()
    payload = build_evaluation_payload(event)

    assert payload["event_id"] == str(event.event_id)
    assert payload["incident_id"] == str(event.incident_id)
    assert payload["root_cause"] == "service_outage"
    assert payload["root_cause_confidence_score"] == 85
    assert payload["root_cause_explanation"] == "service_outage identified with critical anomaly severity"
    assert payload["root_cause_evidence_count"] == 1
    assert payload["root_cause_id"] == str(event.root_cause.id)
    assert payload["business_impact_overall_score"] == 78
    assert payload["business_impact_explanation"] == "Overall business impact is high."
    assert payload["assessment_id"] == str(event.assessment.assessment_id)


def test_event_id_is_identical_across_both_payloads_but_distinct_from_incident_id():
    event = _event()
    recommendation_payload = build_recommendation_payload(event)
    evaluation_payload = build_evaluation_payload(event)

    assert recommendation_payload["event_id"] == evaluation_payload["event_id"] == str(event.event_id)
    assert event.event_id != event.incident_id
    assert recommendation_payload["event_id"] != recommendation_payload["incident"]["incident_id"]
    assert evaluation_payload["event_id"] != evaluation_payload["incident_id"]


def test_evidence_count_reflects_the_real_list_length_not_a_fabricated_value():
    event = _event()
    object.__setattr__(
        event.root_cause, "evidence", [{"a": 1}, {"b": 2}, {"c": 3}]
    )  # frozen dataclass -- direct mutation only for this one assertion
    payload = build_evaluation_payload(event)
    assert payload["root_cause_evidence_count"] == 3


# ---------------------------------------------------------------------------
# Parallel fan-out
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_publish_delivers_to_both_destinations():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(202, json={"outcome": "completed"})

    publisher = _publisher(handler)
    results = await publisher.publish(_event())

    assert len(calls) == 2
    assert any("recommendation_service" in url for url in calls)
    assert any("evaluation_service" in url for url in calls)
    assert all(result.delivered for result in results)


@pytest.mark.anyio
async def test_fan_out_is_parallel_not_sequential():
    """One slow destination must not delay the other -- proves asyncio.gather concurrency, not a regression into chained delivery."""

    async def handler(request: httpx.Request) -> httpx.Response:
        if "recommendation_service" in str(request.url):
            await asyncio.sleep(0.2)
        return httpx.Response(202, json={"outcome": "completed"})

    publisher = _publisher(handler)

    started = time.monotonic()
    await publisher.publish(_event())
    elapsed = time.monotonic() - started

    # Sequential delivery would take >= 0.2s (recommendation's sleep) plus
    # evaluation's own request; parallel delivery takes ~0.2s total. 0.35s
    # leaves comfortable margin without being so loose it can't fail.
    assert elapsed < 0.35


@pytest.mark.anyio
async def test_recommendation_failure_does_not_prevent_evaluation_delivery():
    async def handler(request: httpx.Request) -> httpx.Response:
        if "recommendation_service" in str(request.url):
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(202, json={"outcome": "completed"})

    publisher = _publisher(handler)
    results = await publisher.publish(_event())

    by_destination = {result.destination: result for result in results}
    assert by_destination["recommendation_service"].delivered is False
    assert by_destination["evaluation_service"].delivered is True


@pytest.mark.anyio
async def test_evaluation_failure_does_not_prevent_recommendation_delivery():
    async def handler(request: httpx.Request) -> httpx.Response:
        if "evaluation_service" in str(request.url):
            return httpx.Response(500)
        return httpx.Response(202, json={"outcome": "completed"})

    publisher = _publisher(handler)
    results = await publisher.publish(_event())

    by_destination = {result.destination: result for result in results}
    assert by_destination["evaluation_service"].delivered is False
    assert by_destination["evaluation_service"].detail == "http_500"
    assert by_destination["recommendation_service"].delivered is True


@pytest.mark.anyio
async def test_both_consumers_failing_is_reported_for_each_independently():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    publisher = _publisher(handler)
    results = await publisher.publish(_event())

    assert len(results) == 2
    assert all(not result.delivered for result in results)
    assert {result.destination for result in results} == {"recommendation_service", "evaluation_service"}


@pytest.mark.anyio
async def test_timeout_is_reported_as_a_failed_delivery_not_raised():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    publisher = _publisher(handler)
    results = await publisher.publish(_event())

    assert all(result.delivered is False and result.detail == "timeout" for result in results)


@pytest.mark.anyio
async def test_4xx_response_is_reported_as_a_failed_delivery():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "malformed"})

    publisher = _publisher(handler)
    results = await publisher.publish(_event())

    assert all(result.delivered is False and result.detail == "http_422" for result in results)


@pytest.mark.anyio
async def test_5xx_response_is_reported_as_a_failed_delivery():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    publisher = _publisher(handler)
    results = await publisher.publish(_event())

    assert all(result.delivered is False and result.detail == "http_500" for result in results)
