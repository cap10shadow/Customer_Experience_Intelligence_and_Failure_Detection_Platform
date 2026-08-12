from backend.services.gateway_service.app.core.config import GatewaySettings


def test_default_downstream_urls_cover_all_eight_services():
    gateway_settings = GatewaySettings(_env_file=None)

    urls = gateway_settings.downstream_service_urls

    assert set(urls.keys()) == {
        "ingestion",
        "nlp",
        "anomaly",
        "root_cause",
        "business_impact",
        "recommendation",
        "copilot",
        "evaluation",
    }
    assert urls["anomaly"] == "http://localhost:8003"
    assert urls["evaluation"] == "http://localhost:8008"


def test_downstream_urls_are_overridable_via_env(monkeypatch):
    monkeypatch.setenv("ANOMALY_SERVICE_URL", "http://anomaly_service:8003")

    gateway_settings = GatewaySettings(_env_file=None)

    assert gateway_settings.downstream_service_urls["anomaly"] == "http://anomaly_service:8003"


def test_cors_allowed_origins_parses_comma_separated_string():
    gateway_settings = GatewaySettings(_env_file=None, CORS_ALLOWED_ORIGINS="http://localhost:3000, http://localhost:5173")

    assert gateway_settings.cors_allowed_origins == ["http://localhost:3000", "http://localhost:5173"]


def test_downstream_timeout_has_a_bounded_default():
    gateway_settings = GatewaySettings(_env_file=None)

    assert gateway_settings.DOWNSTREAM_TIMEOUT_SECONDS > 0
