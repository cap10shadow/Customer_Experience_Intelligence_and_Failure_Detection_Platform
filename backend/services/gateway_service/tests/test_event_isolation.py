"""
Part 6 regression protection: the Gateway is not part of the
BusinessImpactCompleted event path (Batch 4B/4C) -- it must never route
`/internal/events/*`, under any prefix, public or otherwise. These tests
fail loudly if a future change ever adds such a route.
"""

from fastapi.testclient import TestClient

from backend.services.gateway_service.app.main import app


def test_internal_events_path_is_not_routed_at_all():
    with TestClient(app) as client:
        response = client.post(
            "/internal/events/business-impact-completed",
            json={"event_id": "does-not-matter"},
        )
    assert response.status_code == 404


def test_internal_events_path_is_not_routed_under_the_public_api_prefix():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/internal/events/business-impact-completed",
            json={"event_id": "does-not-matter"},
        )
    assert response.status_code == 404


def test_no_route_anywhere_on_the_gateway_contains_internal_events():
    internal_event_paths = [route.path for route in app.routes if "internal" in getattr(route, "path", "")]
    assert internal_event_paths == []


def test_gateway_settings_expose_no_internal_events_concept():
    from backend.services.gateway_service.app.core.config import settings

    for url in settings.downstream_service_urls.values():
        assert "internal" not in url
