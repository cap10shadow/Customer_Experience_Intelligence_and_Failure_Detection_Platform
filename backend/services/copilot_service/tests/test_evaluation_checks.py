"""
Direct, deterministic unit tests for each of the nine evaluation
dimensions (architecture §26) against hand-built `CopilotQueryResponse`
fixtures -- exercises the real check *logic*, not just object
construction, without depending on a live database, a live LLM, or any
downstream domain service being reachable.
"""

from backend.services.copilot_service.app.evaluation import checks
from backend.services.copilot_service.app.evaluation.dataset import CaseExpectations, EvaluationCase, ScriptedFinalAnswerSpec
from backend.services.copilot_service.app.evaluation.results import CheckStatus, Dimension
from backend.services.copilot_service.app.schemas.copilot import CopilotQueryResponse, EvidenceReference


def _case(**expectations_kwargs) -> EvaluationCase:
    return EvaluationCase(
        case_id="c1",
        category="test",
        description="test fixture",
        message="hello",
        expectations=CaseExpectations(**expectations_kwargs),
    )


def _response(**kwargs) -> CopilotQueryResponse:
    defaults = dict(
        answer="answer",
        key_findings=[],
        evidence_references=[],
        related_entities=[],
        visualization_hint=None,
        limitations=[],
        conversation_id="conv-1",
        request_id="req-1",
    )
    defaults.update(kwargs)
    return CopilotQueryResponse(**defaults)


def _evidence(source_type="root_cause", source_id="INC-1", evidence_id=None):
    return EvidenceReference(
        evidence_id=evidence_id or f"{source_type}:{source_id}", source_type=source_type, source_id=source_id
    )


# --- tool selection ---------------------------------------------------------------


def test_tool_selection_not_applicable_when_case_defines_no_expectation():
    result = checks.check_tool_selection(_case(), _response())
    assert result.status == CheckStatus.NOT_APPLICABLE


def test_tool_selection_passes_when_expected_tool_evidenced():
    response = _response(evidence_references=[_evidence(source_type="root_cause")])
    result = checks.check_tool_selection(_case(expected_tool_names=["root_cause"]), response)
    assert result.status == CheckStatus.PASS


def test_tool_selection_passes_when_expected_tool_mentioned_in_limitations_even_without_evidence():
    response = _response(limitations=["The tool 'root_cause' found no matching data."])
    result = checks.check_tool_selection(_case(expected_tool_names=["root_cause"]), response)
    assert result.status == CheckStatus.PASS


def test_tool_selection_fails_when_expected_tool_never_appears():
    result = checks.check_tool_selection(_case(expected_tool_names=["root_cause"]), _response())
    assert result.status == CheckStatus.FAIL


def test_tool_selection_fails_when_a_forbidden_tool_was_actually_executed():
    response = _response(evidence_references=[_evidence(source_type="business_impact")])
    result = checks.check_tool_selection(_case(forbidden_tool_names=["business_impact"]), response)
    assert result.status == CheckStatus.FAIL


def test_tool_selection_passes_when_forbidden_tool_was_only_rejected_never_executed():
    response = _response(limitations=["An unavailable tool ('mutate_thing') was requested and was not called."])
    result = checks.check_tool_selection(_case(forbidden_tool_names=["mutate_thing"]), response)
    assert result.status == CheckStatus.PASS


# --- answer grounding ---------------------------------------------------------------


def test_answer_grounding_not_applicable_without_expectation():
    assert checks.check_answer_grounding(_case(), _response()).status == CheckStatus.NOT_APPLICABLE


def test_answer_grounding_fails_when_evidence_expected_but_absent():
    result = checks.check_answer_grounding(_case(expect_nonempty_evidence=True), _response())
    assert result.status == CheckStatus.FAIL


def test_answer_grounding_passes_when_evidence_expected_and_present():
    response = _response(evidence_references=[_evidence()])
    result = checks.check_answer_grounding(_case(expect_nonempty_evidence=True), response)
    assert result.status == CheckStatus.PASS


def test_answer_grounding_fails_when_no_evidence_expected_but_some_present():
    response = _response(evidence_references=[_evidence()])
    result = checks.check_answer_grounding(_case(expect_empty_evidence=True), response)
    assert result.status == CheckStatus.FAIL


# --- citation correctness ---------------------------------------------------------------


def test_citation_correctness_not_applicable_with_no_evidence():
    assert checks.check_citation_correctness(_case(), _response()).status == CheckStatus.NOT_APPLICABLE


def test_citation_correctness_passes_for_well_formed_evidence():
    response = _response(evidence_references=[_evidence()])
    assert checks.check_citation_correctness(_case(), response).status == CheckStatus.PASS


def test_citation_correctness_fails_for_evidence_missing_a_required_field():
    malformed = EvidenceReference(evidence_id="", source_type="root_cause", source_id="INC-1")
    response = _response(evidence_references=[malformed])
    assert checks.check_citation_correctness(_case(), response).status == CheckStatus.FAIL


# --- hallucination ---------------------------------------------------------------


def test_hallucination_not_applicable_without_forbidden_ids():
    assert checks.check_hallucination(_case(), _response()).status == CheckStatus.NOT_APPLICABLE


def test_hallucination_passes_supported_when_fabricated_id_never_appears():
    result = checks.check_hallucination(_case(forbidden_evidence_ids=["fake:1"]), _response())
    assert result.status == CheckStatus.PASS
    assert "SUPPORTED" in result.detail


def test_hallucination_fails_unsupported_when_fabricated_id_leaks_through():
    response = _response(evidence_references=[_evidence(evidence_id="fake:1")])
    result = checks.check_hallucination(_case(forbidden_evidence_ids=["fake:1"]), response)
    assert result.status == CheckStatus.FAIL
    assert "UNSUPPORTED" in result.detail


# --- conflict handling ---------------------------------------------------------------


def test_conflict_handling_not_applicable_when_not_expected():
    assert checks.check_conflict_handling(_case(), _response()).status == CheckStatus.NOT_APPLICABLE


def test_conflict_handling_passes_when_scripted_conflict_text_is_surfaced():
    case = EvaluationCase(
        case_id="c",
        category="t",
        description="d",
        message="m",
        scripted_decisions=[ScriptedFinalAnswerSpec(type="final_answer", answer="a", conflicts=["sources disagree"])],
        expectations=CaseExpectations(expect_conflict_disclosure=True),
    )
    response = _response(limitations=["sources disagree"])
    assert checks.check_conflict_handling(case, response).status == CheckStatus.PASS


def test_conflict_handling_fails_when_conflict_never_surfaces():
    case = EvaluationCase(
        case_id="c",
        category="t",
        description="d",
        message="m",
        scripted_decisions=[ScriptedFinalAnswerSpec(type="final_answer", answer="a", conflicts=["sources disagree"])],
        expectations=CaseExpectations(expect_conflict_disclosure=True),
    )
    assert checks.check_conflict_handling(case, _response()).status == CheckStatus.FAIL


# --- unsupported request handling ---------------------------------------------------------------


def test_unsupported_request_not_applicable_when_not_expected():
    assert checks.check_unsupported_request_handling(_case(), _response()).status == CheckStatus.NOT_APPLICABLE


def test_unsupported_request_passes_on_honest_refusal():
    response = _response(limitations=["No tool can answer this."])
    result = checks.check_unsupported_request_handling(_case(expect_refusal=True), response)
    assert result.status == CheckStatus.PASS


def test_unsupported_request_fails_if_evidence_was_fabricated_instead_of_refusing():
    response = _response(evidence_references=[_evidence()], limitations=["No tool can answer this."])
    result = checks.check_unsupported_request_handling(_case(expect_refusal=True), response)
    assert result.status == CheckStatus.FAIL


# --- scope preservation ---------------------------------------------------------------


def test_scope_preservation_not_applicable_without_expectation():
    assert checks.check_scope_preservation(_case(), _response()).status == CheckStatus.NOT_APPLICABLE


def test_scope_preservation_passes_when_evidence_matches_requested_incident():
    response = _response(evidence_references=[_evidence(source_type="root_cause", source_id="INC-1")])
    result = checks.check_scope_preservation(_case(expected_incident_id="INC-1"), response)
    assert result.status == CheckStatus.PASS


def test_scope_preservation_fails_when_evidence_references_a_different_incident():
    response = _response(evidence_references=[_evidence(source_type="root_cause", source_id="INC-999")])
    result = checks.check_scope_preservation(_case(expected_incident_id="INC-1"), response)
    assert result.status == CheckStatus.FAIL


# --- safety / read-only ---------------------------------------------------------------


def test_safety_read_only_passes_for_a_normal_response():
    from backend.services.copilot_service.app.services import tools_bootstrap  # noqa: F401

    result = checks.check_safety_read_only(_case(), _response())
    assert result.status == CheckStatus.PASS


def test_safety_read_only_fails_if_response_text_claims_a_mutation_occurred():
    from backend.services.copilot_service.app.services import tools_bootstrap  # noqa: F401

    response = _response(answer="Your recommendation has been approved.")
    result = checks.check_safety_read_only(_case(), response)
    assert result.status == CheckStatus.FAIL


# --- completeness ---------------------------------------------------------------


def test_completeness_not_applicable_without_expectation():
    assert checks.check_completeness(_case(), _response()).status == CheckStatus.NOT_APPLICABLE


def test_completeness_passes_when_all_expected_source_types_present():
    response = _response(
        evidence_references=[_evidence(source_type="root_cause"), _evidence(source_type="business_impact")]
    )
    result = checks.check_completeness(_case(expected_source_types=["root_cause", "business_impact"]), response)
    assert result.status == CheckStatus.PASS


def test_completeness_fails_when_an_expected_source_type_is_missing():
    response = _response(evidence_references=[_evidence(source_type="root_cause")])
    result = checks.check_completeness(_case(expected_source_types=["root_cause", "business_impact"]), response)
    assert result.status == CheckStatus.FAIL


def test_all_nine_dimensions_are_covered_by_all_checks_tuple():
    covered = {check(_case(), _response()).dimension for check in checks.ALL_CHECKS}
    assert covered == set(Dimension)
