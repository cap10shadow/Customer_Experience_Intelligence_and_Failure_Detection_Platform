from backend.services.evaluation_service.app.domain.evaluation_rating import EvaluationRating
from backend.services.evaluation_service.app.domain.explainability_engine import ExplainabilityEngine


def test_full_signal_scores_100_and_rates_high(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause_explanation="A" * 20,
        root_cause_evidence_count=3,
        business_impact_explanation="B" * 60,
    )

    result = ExplainabilityEngine().evaluate(context)

    assert result.explainability_score == 100
    assert result.explainability_rating == EvaluationRating.HIGH
    assert len(result.findings) == 4


def test_short_explanations_earn_no_points(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause_explanation="short",
        root_cause_evidence_count=0,
        business_impact_explanation="short",
    )

    result = ExplainabilityEngine().evaluate(context)

    assert result.explainability_score == 0
    assert result.explainability_rating == EvaluationRating.LOW
    assert result.findings == ("No explainability signals were present in the completed intelligence",)


def test_no_evidence_does_not_earn_evidence_points(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause_explanation="A" * 20, root_cause_evidence_count=0, business_impact_explanation="short",
    )

    result = ExplainabilityEngine().evaluate(context)

    assert "Root cause is backed by at least one evidence entry" not in result.findings
    assert result.explainability_score == 30  # explanation present only


def test_detailed_business_impact_explanation_earns_bonus_points(make_domain_evaluation_context):
    short_but_substantive = "B" * 20  # > 10, but not > 50
    detailed = "B" * 60  # > 50

    short_result = ExplainabilityEngine().evaluate(
        make_domain_evaluation_context(
            root_cause_explanation="short", root_cause_evidence_count=0, business_impact_explanation=short_but_substantive
        )
    )
    detailed_result = ExplainabilityEngine().evaluate(
        make_domain_evaluation_context(
            root_cause_explanation="short", root_cause_evidence_count=0, business_impact_explanation=detailed
        )
    )

    assert short_result.explainability_score == 30
    assert detailed_result.explainability_score == 30 + 20


def test_explainability_score_never_exceeds_max(make_domain_evaluation_context):
    result = ExplainabilityEngine().evaluate(make_domain_evaluation_context())

    assert 0 <= result.explainability_score <= 100


def test_is_deterministic(make_domain_evaluation_context):
    context = make_domain_evaluation_context()
    engine = ExplainabilityEngine()

    assert engine.evaluate(context) == engine.evaluate(context)


def test_never_depends_on_quality_engine_output():
    """
    Independence check: ExplainabilityEngine.evaluate accepts only a
    CompletedIntelligence -- there is no parameter through which it could
    receive or call QualityEngine.
    """
    import inspect

    signature = inspect.signature(ExplainabilityEngine.evaluate)
    assert list(signature.parameters.keys()) == ["self", "context"]
