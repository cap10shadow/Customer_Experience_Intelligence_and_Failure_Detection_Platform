import dataclasses

import pytest

from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext


def test_requires_incident(make_business_impact_summary):
    with pytest.raises(ValueError, match="Incident"):
        IntelligenceContext(incident=None, business_impact=make_business_impact_summary())


def test_requires_business_impact(make_incident):
    with pytest.raises(ValueError, match="BusinessImpact"):
        IntelligenceContext(incident=make_incident(), business_impact=None)


def test_root_cause_nlp_and_anomaly_default_to_none(make_incident, make_business_impact_summary):
    context = IntelligenceContext(incident=make_incident(), business_impact=make_business_impact_summary())

    assert context.root_cause is None
    assert context.nlp_intelligence is None
    assert context.anomaly_intelligence is None


def test_carries_every_optional_constituent_when_supplied(
    make_incident, make_business_impact_summary, make_root_cause, make_nlp_intelligence, make_anomaly_intelligence
):
    context = IntelligenceContext(
        incident=make_incident(),
        business_impact=make_business_impact_summary(),
        root_cause=make_root_cause(),
        nlp_intelligence=make_nlp_intelligence(),
        anomaly_intelligence=make_anomaly_intelligence(),
    )

    assert context.root_cause is not None
    assert context.nlp_intelligence is not None
    assert context.anomaly_intelligence is not None


def test_is_immutable(make_intelligence_context):
    context = make_intelligence_context()
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.incident = None
