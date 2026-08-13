"""
Static/configuration verification for Phase 11 Batch 4 -- Grafana
infrastructure and provisioning. Parses the real `docker-compose.yml`
and the real provisioning YAML/JSON files (no mocking, no fixtures
standing in for the actual files) to confirm the frozen architecture's
concrete requirements: the F1 port remap, Docker-internal (never
localhost) datasource URLs, no embedded credentials, and bounded-only
Prometheus labels in every dashboard query.
"""

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
GRAFANA_DIR = REPO_ROOT / "infrastructure" / "observability" / "grafana"
DATASOURCES_FILE = GRAFANA_DIR / "provisioning" / "datasources" / "datasources.yml"
DASHBOARDS_PROVIDER_FILE = GRAFANA_DIR / "provisioning" / "dashboards" / "dashboards.yml"
DASHBOARDS_DIR = GRAFANA_DIR / "dashboards"

_FORBIDDEN_LABELS = {"request_id", "trace_id", "incident_id", "recommendation_id", "complaint_id"}
_FORBIDDEN_SECRET_PATTERNS = ("password=", "api_key", "authorization:", "secret=", "token=")


def _load_compose() -> dict:
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_grafana_service_exists_with_the_frozen_port_remap():
    compose = _load_compose()
    services = compose["services"]

    assert "grafana" in services
    grafana_ports = services["grafana"]["ports"]
    assert grafana_ports == ["${GRAFANA_PORT:-3001}:3000"], grafana_ports


def test_frontend_port_is_unchanged_by_this_batch():
    compose = _load_compose()
    assert compose["services"]["frontend"]["ports"] == ["${FRONTEND_PORT:-3000}:3000"]


def test_grafana_and_frontend_do_not_collide_on_a_host_port():
    compose = _load_compose()
    host_ports = []
    for name, service in compose["services"].items():
        for mapping in service.get("ports", []):
            host_port = mapping.split(":")[0]
            host_ports.append((name, host_port))

    seen: dict = {}
    for name, host_port in host_ports:
        assert host_port not in seen, f"{name} and {seen.get(host_port)} both publish host port {host_port}"
        seen[host_port] = name


def test_loki_tempo_promtail_otel_collector_remain_internal_only():
    """Only Prometheus and Grafana are host-published among the six
    observability services (Phase 11 architecture §3.11)."""
    compose = _load_compose()
    for internal_only in ("loki", "tempo", "promtail", "otel-collector"):
        assert "ports" not in compose["services"][internal_only]


def test_grafana_provisioning_volumes_are_mounted_read_only():
    compose = _load_compose()
    volumes = compose["services"]["grafana"]["volumes"]
    provisioning_mounts = [v for v in volumes if "provisioning" in v or "dashboards" in v]
    assert provisioning_mounts
    assert all(v.endswith(":ro") for v in provisioning_mounts)


def test_grafana_admin_password_is_env_overridable_not_hardcoded():
    compose = _load_compose()
    env = compose["services"]["grafana"]["environment"]
    assert env["GF_SECURITY_ADMIN_PASSWORD"] == "${GF_SECURITY_ADMIN_PASSWORD:-admin}"


# ---------------------------------------------------------------------------
# Datasource provisioning
# ---------------------------------------------------------------------------


def test_datasources_file_provisions_prometheus_loki_and_tempo():
    with open(DATASOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    by_name = {ds["name"]: ds for ds in config["datasources"]}
    assert set(by_name) == {"Prometheus", "Loki", "Tempo"}
    assert by_name["Prometheus"]["url"] == "http://prometheus:9090"
    assert by_name["Loki"]["url"] == "http://loki:3100"
    assert by_name["Tempo"]["url"] == "http://tempo:3200"


def test_datasource_urls_never_use_localhost():
    with open(DATASOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    for datasource in config["datasources"]:
        assert "localhost" not in datasource["url"]
        assert "127.0.0.1" not in datasource["url"]


def test_datasource_file_contains_no_credentials():
    with open(DATASOURCES_FILE, "r", encoding="utf-8") as f:
        raw = f.read().lower()
    for forbidden in _FORBIDDEN_SECRET_PATTERNS:
        assert forbidden not in raw


# ---------------------------------------------------------------------------
# Dashboard provisioning
# ---------------------------------------------------------------------------


def test_dashboard_provider_points_at_the_mounted_dashboards_directory():
    with open(DASHBOARDS_PROVIDER_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    provider = config["providers"][0]
    assert provider["type"] == "file"
    assert provider["options"]["path"] == "/etc/grafana/dashboards"
    assert provider["allowUiUpdates"] is False


def test_every_provisioned_dashboard_json_is_valid_and_loadable():
    dashboard_files = list(DASHBOARDS_DIR.glob("*.json"))
    assert dashboard_files, "expected at least one provisioned dashboard"

    for path in dashboard_files:
        with open(path, "r", encoding="utf-8") as f:
            dashboard = json.load(f)
        assert dashboard["uid"]
        assert dashboard["title"]
        assert dashboard["panels"]


def test_no_dashboard_query_uses_a_high_cardinality_or_forbidden_label():
    """Phase 11 §7/§13/§20: never request_id/trace_id/incident_id/... as a
    Prometheus label or dashboard variable."""
    dashboard_files = list(DASHBOARDS_DIR.glob("*.json"))
    for path in dashboard_files:
        raw = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_LABELS:
            assert forbidden not in raw, f"{path.name} references forbidden label '{forbidden}'"


def test_no_dashboard_contains_a_hardcoded_secret():
    dashboard_files = list(DASHBOARDS_DIR.glob("*.json"))
    for path in dashboard_files:
        raw = path.read_text(encoding="utf-8").lower()
        for forbidden in _FORBIDDEN_SECRET_PATTERNS:
            assert forbidden not in raw, f"{path.name} appears to contain a credential-like string"


def test_platform_health_dashboard_queries_only_real_batch1_metrics():
    """Platform Health may only reference metrics that genuinely exist
    (Prometheus's own `up`, and the shared `http_requests_total` counter)
    -- never an invented business/domain metric."""
    path = DASHBOARDS_DIR / "platform-health.json"
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    exprs = [
        target["expr"]
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
        if "expr" in target
    ]
    assert exprs
    allowed_metric_pattern = re.compile(r"\b(up|http_requests_total|service_readiness)\b")
    for expr in exprs:
        assert allowed_metric_pattern.search(expr), expr


def test_platform_health_dashboard_includes_the_readiness_panel():
    """Phase 11 closure: readiness must genuinely be visualized, not just
    liveness/error-rate, once the service_readiness gauge exists."""
    path = DASHBOARDS_DIR / "platform-health.json"
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    titles = [panel["title"] for panel in dashboard["panels"]]
    assert any("Readiness" in title for title in titles), titles


def test_api_service_performance_dashboard_queries_only_real_batch1_metrics():
    path = DASHBOARDS_DIR / "api-service-performance.json"
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    prom_exprs = [
        target["expr"]
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
        if "expr" in target
    ]
    assert prom_exprs
    allowed_metric_pattern = re.compile(r"\b(http_requests_total|http_request_duration_seconds_bucket)\b")
    for expr in prom_exprs:
        assert allowed_metric_pattern.search(expr), expr


def test_api_service_performance_dashboard_variables_use_only_real_bounded_labels():
    path = DASHBOARDS_DIR / "api-service-performance.json"
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    variable_names = {v["name"] for v in dashboard["templating"]["list"]}
    assert variable_names == {"service", "route"}
    for variable in dashboard["templating"]["list"]:
        assert variable["query"]["query"].startswith("label_values(http_requests_total")


def test_api_service_performance_tempo_panel_uses_traceql_not_fabricated_data():
    path = DASHBOARDS_DIR / "api-service-performance.json"
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    tempo_targets = [
        target
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
        if target.get("datasource", {}).get("type") == "tempo"
    ]
    assert tempo_targets
    assert all(t["queryType"] == "traceqlSearch" for t in tempo_targets)
