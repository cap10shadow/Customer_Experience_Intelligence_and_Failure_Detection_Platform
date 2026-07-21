from backend.services.root_cause_service.app.services.scoring import MAX_SCORE, cap_score


def test_cap_score_within_range_unchanged():
    assert cap_score(55) == 55


def test_cap_score_caps_at_max():
    assert cap_score(250) == MAX_SCORE


def test_cap_score_floors_at_zero():
    assert cap_score(-20) == 0
