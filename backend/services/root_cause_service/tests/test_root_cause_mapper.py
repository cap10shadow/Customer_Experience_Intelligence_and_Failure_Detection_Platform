import uuid

from backend.services.root_cause_service.app.domain.evidence import Evidence, EvidenceType
from backend.services.root_cause_service.app.domain.root_cause_candidate import RootCauseCandidate
from backend.services.root_cause_service.app.mappers.root_cause_mapper import RootCauseMapper
from backend.shared.constants.enums.root_cause import RootCause as RootCauseEnum
from backend.shared.constants.enums.root_cause import RootCauseStatus


def test_maps_candidate_fields_verbatim():
    incident_id = uuid.uuid4()
    candidate = RootCauseCandidate(
        cause=RootCauseEnum.PAYMENT_GATEWAY_FAILURE,
        confidence_score=85,
        confidence_level="High",
        evidence=(Evidence(type=EvidenceType.CATEGORY, description="Payment complaints increased", weight=40),),
        explanation="payment_gateway_failure identified with 85 confidence (High).",
        rule_version="1.0",
    )

    root_cause = RootCauseMapper.to_orm(incident_id, candidate)

    assert root_cause.incident_id == incident_id
    assert root_cause.cause == RootCauseEnum.PAYMENT_GATEWAY_FAILURE
    assert root_cause.confidence_score == 85
    assert root_cause.confidence_level == "High"
    assert root_cause.explanation == candidate.explanation
    assert root_cause.rule_version == "1.0"
    assert root_cause.status == RootCauseStatus.IDENTIFIED


def test_serializes_evidence_to_plain_dicts():
    incident_id = uuid.uuid4()
    candidate = RootCauseCandidate(
        cause=RootCauseEnum.SERVICE_OUTAGE,
        confidence_score=60,
        confidence_level="Medium",
        evidence=(
            Evidence(type=EvidenceType.CATEGORY, description="Technical complaints detected", weight=40),
            Evidence(type=EvidenceType.REGION, description="Regional spike detected", weight=15),
        ),
        explanation="test",
        rule_version="1.0",
    )

    root_cause = RootCauseMapper.to_orm(incident_id, candidate)

    assert root_cause.evidence == [
        {"type": "category", "description": "Technical complaints detected", "weight": 40},
        {"type": "region", "description": "Regional spike detected", "weight": 15},
    ]


def test_maps_unknown_candidate_with_no_evidence():
    incident_id = uuid.uuid4()
    candidate = RootCauseCandidate(
        cause=RootCauseEnum.UNKNOWN,
        confidence_score=0,
        confidence_level="Weak",
        evidence=(),
        explanation="No deterministic rule matched this incident; root cause is unknown.",
        rule_version="1.0",
    )

    root_cause = RootCauseMapper.to_orm(incident_id, candidate)

    assert root_cause.cause == RootCauseEnum.UNKNOWN
    assert root_cause.evidence == []
