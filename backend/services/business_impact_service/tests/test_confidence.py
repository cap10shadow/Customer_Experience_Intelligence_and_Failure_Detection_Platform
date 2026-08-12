from backend.services.business_impact_service.app.domain.confidence import ConfidenceScore, classify_confidence
from backend.services.root_cause_service.app.domain.confidence import classify_confidence as rc_classify_confidence


def test_classify_confidence_boundaries():
    assert classify_confidence(0) == "Low"
    assert classify_confidence(20) == "Low"
    assert classify_confidence(40) == "Low"
    assert classify_confidence(41) == "Moderate"
    assert classify_confidence(60) == "Moderate"
    assert classify_confidence(80) == "Moderate"
    assert classify_confidence(81) == "High"
    assert classify_confidence(100) == "High"


def test_classify_confidence_is_deterministic():
    for score in range(0, 101):
        assert classify_confidence(score) == classify_confidence(score)


def test_confidence_score_from_score_classifies_correctly():
    confidence = ConfidenceScore.from_score(60)
    assert confidence.score == 60
    assert confidence.band == "Moderate"


def test_confidence_score_clamps_above_100():
    confidence = ConfidenceScore.from_score(250)
    assert confidence.score == 100
    assert confidence.band == "High"


def test_confidence_score_clamps_below_0():
    confidence = ConfidenceScore.from_score(-10)
    assert confidence.score == 0
    assert confidence.band == "Low"


def test_only_the_six_real_discrete_scores_produced_by_compute_confidence_classify_sensibly():
    """
    scoring.compute_confidence() can only ever produce round((n/5)*100) for
    n in 0..5 -- i.e. exactly these six values. Confirms each maps to the
    intended completeness band (see domain/confidence.py's rationale).
    """
    expected = {
        0: "Low",  # 0/5 informative
        20: "Low",  # 1/5
        40: "Low",  # 2/5
        60: "Moderate",  # 3/5
        80: "Moderate",  # 4/5
        100: "High",  # 5/5
    }
    for score, band in expected.items():
        assert classify_confidence(score) == band


def test_business_impact_bands_are_independent_of_root_cause_bands():
    """
    ARB-008: Business Impact's classifier must never be reused for or by
    Root Cause, and the two must be free to disagree on the same raw
    number -- 41 is a real disagreement (BI: "Moderate", RC: "Low"),
    proving the two functions are genuinely independent, not aliases of
    the same underlying logic.
    """
    assert classify_confidence(41) == "Moderate"
    assert rc_classify_confidence(41) == "Low"
    assert classify_confidence is not rc_classify_confidence
