from backend.services.evaluation_service.app.domain.confidence_analyzer import ConfidenceAnalyzer


def test_summarizes_existing_confidence_values_verbatim(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause_confidence_score=80, business_impact_confidence=60,
    )

    result = ConfidenceAnalyzer().summarize(context)

    assert result.root_cause_confidence == 80
    assert result.business_impact_confidence == 60
    assert result.average_confidence == 70.0


def test_average_confidence_handles_asymmetric_values(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause_confidence_score=100, business_impact_confidence=0,
    )

    result = ConfidenceAnalyzer().summarize(context)

    assert result.average_confidence == 50.0


def test_equal_confidence_values_produce_equal_average(make_domain_evaluation_context):
    context = make_domain_evaluation_context(
        root_cause_confidence_score=45, business_impact_confidence=45,
    )

    result = ConfidenceAnalyzer().summarize(context)

    assert result.average_confidence == 45.0


def test_never_recalculates_confidence_it_only_reads_existing_values(make_domain_evaluation_context):
    # If the analyzer ever started deriving its own confidence (e.g. from
    # root_cause/business_impact_overall_score), this test would catch it:
    # root_cause_confidence_score and business_impact_confidence are the
    # ONLY fields the summary may be built from.
    context = make_domain_evaluation_context(
        root_cause_confidence_score=33,
        business_impact_confidence=77,
        business_impact_overall_score=0,  # deliberately inconsistent with confidence, to prove it's ignored
    )

    result = ConfidenceAnalyzer().summarize(context)

    assert result.root_cause_confidence == 33
    assert result.business_impact_confidence == 77
    assert result.average_confidence == 55.0


def test_is_deterministic(make_domain_evaluation_context):
    context = make_domain_evaluation_context()
    analyzer = ConfidenceAnalyzer()

    assert analyzer.summarize(context) == analyzer.summarize(context)
