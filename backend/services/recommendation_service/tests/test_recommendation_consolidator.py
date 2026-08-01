from backend.services.recommendation_service.app.domain import scoring
from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_consolidator import RecommendationConsolidator
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence


def _evidence(description="evidence", weight=10, source=EvidenceSource.INCIDENT) -> SupportingEvidence:
    return SupportingEvidence(source=source, description=description, weight=weight)


def _recommendation(
    *,
    incident_id="INC-1",
    category=RecommendationCategory.MONITOR,
    action="Monitor.",
    priority=RecommendationPriority.LOW,
    score=None,
    rationale="rationale",
    priority_rationale="priority rationale",
    evidence=None,
) -> Recommendation:
    supporting_evidence = evidence if evidence is not None else (_evidence(),)
    return Recommendation(
        incident_id=incident_id,
        category=category,
        action=action,
        priority=priority,
        score=score if score is not None else scoring.compute_score(priority, supporting_evidence),
        rationale=rationale,
        priority_rationale=priority_rationale,
        supporting_evidence=supporting_evidence,
    )


def test_empty_input_produces_empty_output():
    assert RecommendationConsolidator().consolidate(()) == ()


def test_single_recommendation_passes_through_unchanged():
    recommendation = _recommendation()

    result = RecommendationConsolidator().consolidate((recommendation,))

    assert result == (recommendation,)


def test_removes_exact_duplicates():
    recommendation = _recommendation()

    result = RecommendationConsolidator().consolidate((recommendation, recommendation, recommendation))

    assert result == (recommendation,)


def test_merges_equivalent_recommendations_from_different_rules():
    first = _recommendation(
        category=RecommendationCategory.ESCALATE,
        action="Escalate now.",
        priority=RecommendationPriority.HIGH,
        rationale="Reason A.",
        priority_rationale="Priority reason A.",
        evidence=(_evidence("signal one", weight=10),),
    )
    second = _recommendation(
        category=RecommendationCategory.ESCALATE,
        action="Escalate now.",
        priority=RecommendationPriority.CRITICAL,
        rationale="Reason B.",
        priority_rationale="Priority reason B.",
        evidence=(_evidence("signal two", weight=15),),
    )

    result = RecommendationConsolidator().consolidate((first, second))

    assert len(result) == 1
    merged = result[0]
    assert merged.category == RecommendationCategory.ESCALATE
    assert merged.action == "Escalate now."
    assert merged.priority == RecommendationPriority.CRITICAL  # more urgent of the two wins
    assert len(merged.supporting_evidence) == 2  # union of both rules' evidence
    assert "Reason A." in merged.rationale and "Reason B." in merged.rationale
    # Merged score is policy-derived from the union of evidence, not an ad-hoc max/average.
    assert merged.score == scoring.compute_score(RecommendationPriority.CRITICAL, merged.supporting_evidence)


def test_merge_deduplicates_identical_evidence_across_the_group():
    shared_evidence = _evidence("shared signal", weight=10)
    first = _recommendation(
        category=RecommendationCategory.MITIGATE, action="Mitigate.", evidence=(shared_evidence, _evidence("unique one", 5))
    )
    second = _recommendation(
        category=RecommendationCategory.MITIGATE, action="Mitigate.", evidence=(shared_evidence, _evidence("unique two", 5))
    )

    result = RecommendationConsolidator().consolidate((first, second))

    assert len(result) == 1
    # 3 distinct pieces of evidence: the shared one (deduplicated) + 2 unique ones.
    assert len(result[0].supporting_evidence) == 3


def test_different_actions_in_the_same_category_are_not_merged():
    first = _recommendation(category=RecommendationCategory.MITIGATE, action="Mitigate root cause A.")
    second = _recommendation(category=RecommendationCategory.MITIGATE, action="Mitigate root cause B.")

    result = RecommendationConsolidator().consolidate((first, second))

    assert len(result) == 2


def test_monitor_is_dropped_when_a_conflicting_urgent_category_is_present():
    monitor = _recommendation(category=RecommendationCategory.MONITOR, action="Monitor.")
    escalate = _recommendation(category=RecommendationCategory.ESCALATE, action="Escalate.", priority=RecommendationPriority.CRITICAL)

    result = RecommendationConsolidator().consolidate((monitor, escalate))

    categories = {recommendation.category for recommendation in result}
    assert RecommendationCategory.MONITOR not in categories
    assert RecommendationCategory.ESCALATE in categories


def test_monitor_is_kept_when_no_conflicting_category_is_present():
    monitor = _recommendation(category=RecommendationCategory.MONITOR, action="Monitor.")
    investigate = _recommendation(category=RecommendationCategory.INVESTIGATE, action="Investigate.")

    result = RecommendationConsolidator().consolidate((monitor, investigate))

    categories = {recommendation.category for recommendation in result}
    assert RecommendationCategory.MONITOR in categories
    assert RecommendationCategory.INVESTIGATE in categories


def test_monitor_alone_is_never_dropped():
    monitor = _recommendation(category=RecommendationCategory.MONITOR, action="Monitor.")

    result = RecommendationConsolidator().consolidate((monitor,))

    assert result == (monitor,)


def test_orders_by_priority_first():
    # INVESTIGATE and ESCALATE are not in MONITOR_CONFLICTS_WITH's scope
    # (conflict resolution only ever drops MONITOR) -- both are kept here,
    # isolating the ordering behavior this test targets.
    low = _recommendation(category=RecommendationCategory.INVESTIGATE, priority=RecommendationPriority.LOW, action="Investigate.")
    critical = _recommendation(category=RecommendationCategory.ESCALATE, priority=RecommendationPriority.CRITICAL, action="Escalate.")

    result = RecommendationConsolidator().consolidate((low, critical))

    assert result[0] is critical
    assert result[1] is low


def test_orders_by_category_precedence_when_priority_ties():
    investigate = _recommendation(category=RecommendationCategory.INVESTIGATE, action="Investigate.", priority=RecommendationPriority.MEDIUM)
    mitigate = _recommendation(category=RecommendationCategory.MITIGATE, action="Mitigate.", priority=RecommendationPriority.MEDIUM)

    result = RecommendationConsolidator().consolidate((investigate, mitigate))

    assert result[0].category == RecommendationCategory.MITIGATE  # higher category precedence than INVESTIGATE
    assert result[1].category == RecommendationCategory.INVESTIGATE


def test_orders_by_score_descending_when_priority_and_category_tie():
    lower_score = _recommendation(
        category=RecommendationCategory.MONITOR, priority=RecommendationPriority.LOW, evidence=(_evidence(weight=0),)
    )
    higher_score = _recommendation(
        category=RecommendationCategory.MONITOR,
        action="Monitor more closely.",
        priority=RecommendationPriority.LOW,
        evidence=(_evidence(weight=20),),
    )

    result = RecommendationConsolidator().consolidate((lower_score, higher_score))

    assert result[0] is higher_score
    assert result[1] is lower_score


def test_rule_evaluation_order_is_the_final_tiebreak():
    """
    Two Recommendations with identical priority, category, and score (but
    different, non-equivalent actions, so they are not merged) must retain
    their original rule-evaluation order.
    """
    first_evaluated = _recommendation(category=RecommendationCategory.MONITOR, action="Monitor A.")
    second_evaluated = _recommendation(category=RecommendationCategory.MONITOR, action="Monitor B.")

    result = RecommendationConsolidator().consolidate((first_evaluated, second_evaluated))

    assert result == (first_evaluated, second_evaluated)


def test_ordering_is_deterministic_across_repeated_calls():
    recommendations = (
        _recommendation(category=RecommendationCategory.MONITOR, action="A"),
        _recommendation(category=RecommendationCategory.ESCALATE, action="B", priority=RecommendationPriority.CRITICAL),
        _recommendation(category=RecommendationCategory.INVESTIGATE, action="C"),
    )

    first = RecommendationConsolidator().consolidate(recommendations)
    second = RecommendationConsolidator().consolidate(recommendations)

    assert first == second


def test_never_introduces_a_recommendation_not_present_in_the_input():
    recommendations = (
        _recommendation(category=RecommendationCategory.MONITOR, action="A"),
        _recommendation(category=RecommendationCategory.ESCALATE, action="B"),
    )

    result = RecommendationConsolidator().consolidate(recommendations)

    input_keys = {(recommendation.category, recommendation.action) for recommendation in recommendations}
    result_keys = {(recommendation.category, recommendation.action) for recommendation in result}
    assert result_keys.issubset(input_keys)
