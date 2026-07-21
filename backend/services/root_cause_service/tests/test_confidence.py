from backend.services.root_cause_service.app.domain.confidence import ConfidenceScore, classify_confidence


def test_classify_confidence_boundaries():
    assert classify_confidence(0) == "Weak"
    assert classify_confidence(30) == "Weak"
    assert classify_confidence(31) == "Low"
    assert classify_confidence(50) == "Low"
    assert classify_confidence(51) == "Medium"
    assert classify_confidence(70) == "Medium"
    assert classify_confidence(71) == "High"
    assert classify_confidence(90) == "High"
    assert classify_confidence(91) == "Very High"
    assert classify_confidence(100) == "Very High"


def test_confidence_score_from_score_classifies_correctly():
    confidence = ConfidenceScore.from_score(85)
    assert confidence.score == 85
    assert confidence.band == "High"


def test_confidence_score_clamps_above_100():
    confidence = ConfidenceScore.from_score(250)
    assert confidence.score == 100
    assert confidence.band == "Very High"


def test_confidence_score_clamps_below_0():
    confidence = ConfidenceScore.from_score(-10)
    assert confidence.score == 0
    assert confidence.band == "Weak"
