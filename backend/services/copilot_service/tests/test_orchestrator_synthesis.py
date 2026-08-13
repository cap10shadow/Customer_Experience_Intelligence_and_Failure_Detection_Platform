"""
Tests for the Phase 12 Batch 3 response-synthesis layer
(orchestrator/synthesis.py) -- evidence-ID filtering, related-entity
derivation, visualization-hint validation, and freshness passthrough.
"""

from backend.services.copilot_service.app.schemas.copilot import EvidenceReference
from backend.services.copilot_service.app.services.orchestrator.state import FinalAnswerDecision, OrchestrationState
from backend.services.copilot_service.app.services.orchestrator.synthesis import synthesize_response


def _state(**overrides) -> OrchestrationState:
    base: OrchestrationState = {
        "conversation_id": "conv-1",
        "request_id": "req-1",
        "evidence_references": [],
        "limitations": [],
        "final_answer": FinalAnswerDecision(answer="default"),
    }
    base.update(overrides)
    return base


def test_response_conforms_to_the_frozen_contract_field_set():
    response = synthesize_response(_state())
    assert set(response.model_dump().keys()) == {
        "answer",
        "key_findings",
        "evidence_references",
        "related_entities",
        "visualization_hint",
        "limitations",
        "conversation_id",
        "request_id",
    }


def test_model_claimed_but_nonexistent_evidence_id_is_dropped():
    real = EvidenceReference(evidence_id="recommendation:real-1", source_type="recommendation", source_id="real-1")
    state = _state(
        evidence_references=[real],
        final_answer=FinalAnswerDecision(answer="x", evidence_ids=["recommendation:invented"]),
    )

    response = synthesize_response(state)

    # The invented ID was rejected; since the model cited nothing valid,
    # all real evidence is surfaced instead of being silently withheld.
    assert [e.evidence_id for e in response.evidence_references] == ["recommendation:real-1"]


def test_only_cited_real_evidence_is_returned_when_model_cites_a_subset():
    first = EvidenceReference(evidence_id="recommendation:1", source_type="recommendation", source_id="1")
    second = EvidenceReference(evidence_id="root_cause:2", source_type="root_cause", source_id="2")
    state = _state(
        evidence_references=[first, second],
        final_answer=FinalAnswerDecision(answer="x", evidence_ids=["recommendation:1"]),
    )

    response = synthesize_response(state)

    assert [e.evidence_id for e in response.evidence_references] == ["recommendation:1"]


def test_related_entities_are_derived_only_from_real_evidence():
    evidence = [
        EvidenceReference(evidence_id="incident:INC-1", source_type="incident", source_id="INC-1"),
        EvidenceReference(evidence_id="root_cause:RC-1", source_type="root_cause", source_id="RC-1"),
    ]
    state = _state(evidence_references=evidence, final_answer=FinalAnswerDecision(answer="x"))

    response = synthesize_response(state)

    related = {(e.type, e.id) for e in response.related_entities}
    assert related == {("incident", "INC-1"), ("root_cause", "RC-1")}


def test_visualization_hint_kept_when_matching_evidence_exists():
    evidence = [EvidenceReference(evidence_id="trend:x", source_type="trend", source_id="x")]
    state = _state(
        evidence_references=evidence,
        final_answer=FinalAnswerDecision(answer="x", visualization_hint="trend", evidence_ids=["trend:x"]),
    )

    response = synthesize_response(state)
    assert response.visualization_hint == "trend"


def test_visualization_hint_dropped_when_no_supporting_evidence_type():
    evidence = [EvidenceReference(evidence_id="recommendation:1", source_type="recommendation", source_id="1")]
    state = _state(
        evidence_references=evidence,
        final_answer=FinalAnswerDecision(answer="x", visualization_hint="trend", evidence_ids=["recommendation:1"]),
    )

    response = synthesize_response(state)
    assert response.visualization_hint is None


def test_visualization_hint_dropped_when_no_evidence_at_all():
    state = _state(final_answer=FinalAnswerDecision(answer="x", visualization_hint="table"))
    response = synthesize_response(state)
    assert response.visualization_hint is None


def test_freshness_timestamp_is_never_fabricated_only_passed_through():
    with_timestamp = EvidenceReference(
        evidence_id="root_cause:1", source_type="root_cause", source_id="1", timestamp="2026-08-08T00:00:00Z"
    )
    without_timestamp = EvidenceReference(evidence_id="trend:x", source_type="trend", source_id="x", timestamp=None)
    state = _state(evidence_references=[with_timestamp, without_timestamp], final_answer=FinalAnswerDecision(answer="x"))

    response = synthesize_response(state)

    by_id = {e.evidence_id: e.timestamp for e in response.evidence_references}
    assert by_id["root_cause:1"] == "2026-08-08T00:00:00Z"
    assert by_id["trend:x"] is None  # never invented


def test_conflicts_are_disclosed_via_limitations_never_silently_resolved():
    state = _state(
        final_answer=FinalAnswerDecision(
            answer="x", conflicts=["Root Cause reports unconfirmed while Business Impact assumes a confirmed cause."]
        )
    )

    response = synthesize_response(state)

    assert "Root Cause reports unconfirmed while Business Impact assumes a confirmed cause." in response.limitations


def test_limitations_are_merged_and_deduplicated():
    state = _state(
        limitations=["Tool X failed.", "Tool X failed."],
        final_answer=FinalAnswerDecision(answer="x", limitations=["Tool X failed."]),
    )

    response = synthesize_response(state)
    assert response.limitations.count("Tool X failed.") == 1


def test_key_findings_are_passed_through_from_the_model_verbatim():
    state = _state(final_answer=FinalAnswerDecision(answer="x", key_findings=["Score is 88.", "Priority is high."]))
    response = synthesize_response(state)
    assert response.key_findings == ["Score is 88.", "Priority is high."]


def test_no_orchestrator_code_ever_calls_datetime_now_for_evidence_or_answers():
    """Structural check: freshness must only ever come from real tool data, never from wall-clock time."""
    import inspect

    from backend.services.copilot_service.app.services.orchestrator import graph, synthesis

    for module in (graph, synthesis):
        source = inspect.getsource(module)
        assert "datetime.now(" not in source
        assert "utcnow(" not in source
