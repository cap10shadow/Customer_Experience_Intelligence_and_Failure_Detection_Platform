from backend.services.evaluation_service.app.domain.evaluation_rating import EvaluationRating
from backend.services.evaluation_service.app.domain.quality_engine import QualityEngine
from backend.shared.constants.enums.root_cause import RootCause


def test_full_signal_scores_100_and_rates_high(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause=RootCause.SERVICE_OUTAGE,
        root_cause_confidence_score=90,
        business_impact_confidence=90,
        business_impact_overall_score=75,
    )

    result = QualityEngine().evaluate(context)

    assert result.quality_score == 100
    assert result.quality_rating == EvaluationRating.HIGH
    assert len(result.findings) == 4


def test_unknown_root_cause_does_not_earn_identification_points(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause=RootCause.UNKNOWN,
        root_cause_confidence_score=0,
        business_impact_confidence=0,
        business_impact_overall_score=0,
    )

    result = QualityEngine().evaluate(context)

    assert result.quality_score == 0
    assert result.quality_rating == EvaluationRating.LOW
    assert result.findings == ("No quality signals were present in the completed intelligence",)


def test_root_cause_identified_alone_scores_forty(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause=RootCause.SERVICE_OUTAGE,
        root_cause_confidence_score=0,
        business_impact_confidence=0,
        business_impact_overall_score=0,
    )

    result = QualityEngine().evaluate(context)

    assert result.quality_score == 40
    assert result.findings == ("Root cause was identified rather than left unknown",)


def test_low_confidence_does_not_earn_confidence_points(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause_confidence_score=69, business_impact_confidence=69,
    )

    result = QualityEngine().evaluate(context)

    assert "Root cause confidence is high (>= 70)" not in result.findings
    assert "Business impact confidence is high (>= 70)" not in result.findings


def test_confidence_threshold_boundary_earns_points(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause_confidence_score=70, business_impact_confidence=70, business_impact_overall_score=0,
    )

    result = QualityEngine().evaluate(context)

    assert result.quality_score == 40 + 20 + 20  # identified + both confidences high


def test_quality_score_never_exceeds_max(make_domain_evaluation_context):
    result = QualityEngine().evaluate(make_domain_evaluation_context())

    assert 0 <= result.quality_score <= 100


def test_is_deterministic(make_domain_evaluation_context):
    context = make_domain_evaluation_context()
    engine = QualityEngine()

    assert engine.evaluate(context) == engine.evaluate(context)


def test_never_mutates_its_input(make_domain_evaluation_context):
    context = make_domain_evaluation_context()
    original = context

    QualityEngine().evaluate(context)

    assert context is original
    assert context.root_cause_confidence_score == 85  # unchanged (frozen dataclass anyway)
