from backend.services.root_cause_service.app.domain.evidence import Evidence, EvidenceType


def test_evidence_holds_structured_fields():
    evidence = Evidence(type=EvidenceType.CATEGORY, description="Billing complaints increased", weight=30)
    assert evidence.type == EvidenceType.CATEGORY
    assert evidence.description == "Billing complaints increased"
    assert evidence.weight == 30


def test_evidence_is_immutable():
    evidence = Evidence(type=EvidenceType.SEVERITY, description="test", weight=10)
    try:
        evidence.weight = 99
        assert False, "Evidence should be frozen"
    except AttributeError:
        pass
