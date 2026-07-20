from backend.services.anomaly_service.app.services.rules import category_rule


def test_same_category_matches(make_anomaly):
    anomalies = [
        make_anomaly(entity_type="category", entity_value="payment_issue"),
        make_anomaly(entity_type="global", entity_value=None),
        make_anomaly(entity_type="category", entity_value="payment_issue"),
    ]
    result = category_rule.evaluate(anomalies)
    assert result.matched is True
    assert result.points == 20
    assert "payment_issue" in result.reason


def test_different_categories_do_not_match(make_anomaly):
    anomalies = [
        make_anomaly(entity_type="category", entity_value="payment_issue"),
        make_anomaly(entity_type="category", entity_value="delivery_issue"),
    ]
    result = category_rule.evaluate(anomalies)
    assert result.matched is False


def test_single_category_scoped_anomaly_does_not_match(make_anomaly):
    anomalies = [make_anomaly(entity_type="category", entity_value="payment_issue"), make_anomaly(entity_type="global")]
    result = category_rule.evaluate(anomalies)
    assert result.matched is False
