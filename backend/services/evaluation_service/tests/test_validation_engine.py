from backend.services.evaluation_service.app.domain.validation_engine import ValidationEngine


def test_valid_context_passes(make_domain_evaluation_context):
    result = ValidationEngine().validate(make_domain_evaluation_context())

    assert result.is_valid is True
    assert result.reasons == ()


def test_missing_incident_id_fails(make_domain_evaluation_context):
    result = ValidationEngine().validate(make_domain_evaluation_context(incident_id=""))

    assert result.is_valid is False
    assert any("incident_id" in reason for reason in result.reasons)


def test_out_of_range_root_cause_confidence_fails(make_domain_evaluation_context):
    result = ValidationEngine().validate(make_domain_evaluation_context(root_cause_confidence_score=101))

    assert result.is_valid is False
    assert any("root_cause_confidence_score" in reason for reason in result.reasons)


def test_negative_root_cause_confidence_fails(make_domain_evaluation_context):
    result = ValidationEngine().validate(make_domain_evaluation_context(root_cause_confidence_score=-1))

    assert result.is_valid is False
    assert any("root_cause_confidence_score" in reason for reason in result.reasons)


def test_missing_root_cause_explanation_fails(make_domain_evaluation_context):
    result = ValidationEngine().validate(make_domain_evaluation_context(root_cause_explanation=""))

    assert result.is_valid is False
    assert any("root_cause_explanation" in reason for reason in result.reasons)


def test_out_of_range_business_impact_overall_score_fails(make_domain_evaluation_context):
    result = ValidationEngine().validate(make_domain_evaluation_context(business_impact_overall_score=150))

    assert result.is_valid is False
    assert any("business_impact_overall_score" in reason for reason in result.reasons)


def test_out_of_range_business_impact_confidence_fails(make_domain_evaluation_context):
    result = ValidationEngine().validate(make_domain_evaluation_context(business_impact_confidence=-5))

    assert result.is_valid is False
    assert any("business_impact_confidence" in reason for reason in result.reasons)


def test_missing_business_impact_explanation_fails(make_domain_evaluation_context):
    result = ValidationEngine().validate(make_domain_evaluation_context(business_impact_explanation=""))

    assert result.is_valid is False
    assert any("business_impact_explanation" in reason for reason in result.reasons)


def test_multiple_failures_are_all_reported(make_domain_evaluation_context):
    result = ValidationEngine().validate(
        make_domain_evaluation_context(incident_id="", root_cause_explanation="", business_impact_explanation="")
    )

    assert result.is_valid is False
    assert len(result.reasons) == 3


def test_boundary_scores_of_zero_and_hundred_are_valid(make_domain_evaluation_context):
    result = ValidationEngine().validate(
        make_domain_evaluation_context(
            root_cause_confidence_score=0, business_impact_overall_score=100, business_impact_confidence=0
        )
    )

    assert result.is_valid is True


def test_is_deterministic(make_domain_evaluation_context):
    context = make_domain_evaluation_context()
    engine = ValidationEngine()

    assert engine.validate(context) == engine.validate(context)
