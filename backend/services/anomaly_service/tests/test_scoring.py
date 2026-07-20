from backend.services.anomaly_service.app.services.scoring import (
    MAX_CONFIDENCE,
    RuleResult,
    classify_band,
    combine,
)


def test_max_confidence_is_100():
    assert MAX_CONFIDENCE == 100


def test_classify_band_boundaries():
    assert classify_band(0) == "Weak"
    assert classify_band(30) == "Weak"
    assert classify_band(31) == "Possible"
    assert classify_band(60) == "Possible"
    assert classify_band(61) == "Strong"
    assert classify_band(80) == "Strong"
    assert classify_band(81) == "Very Strong"
    assert classify_band(100) == "Very Strong"


def test_combine_sums_matched_points_only():
    results = [
        RuleResult(matched=True, points=25, reason="Same region (South)"),
        RuleResult(matched=False, points=0),
        RuleResult(matched=True, points=20, reason="Same category (billing)"),
    ]
    confidence = combine(results)
    assert confidence.score == 45
    assert confidence.band == "Possible"
    assert confidence.reasons == ["Same region (South)", "Same category (billing)"]


def test_combine_caps_at_max_confidence():
    results = [RuleResult(matched=True, points=60, reason="a"), RuleResult(matched=True, points=60, reason="b")]
    confidence = combine(results)
    assert confidence.score == 100


def test_combine_with_no_matches_is_zero():
    confidence = combine([RuleResult(matched=False, points=0), RuleResult(matched=False, points=0)])
    assert confidence.score == 0
    assert confidence.band == "Weak"
    assert confidence.reasons == []
