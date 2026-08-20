from typing import Any, Dict, List

import httpx

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import get_json, patch_json, post_resource
from backend.services.gateway_service.app.core.errors import DownstreamServiceError
from backend.services.gateway_service.app.schemas.dataset import DatasetVersionResponse
from backend.services.gateway_service.app.services.dataset_proxy import finalize_dataset_version, to_version_response

_INGESTION_DATASETS_URL = f"{settings.INGESTION_SERVICE_URL}/datasets"
_INGESTION_COMPLAINTS_URL = f"{settings.INGESTION_SERVICE_URL}/complaints"
_ENRICH_DAYS_WINDOW = 30
_CORRELATION_WINDOW_MINUTES = 60


async def run_analysis_for_dataset(client: httpx.AsyncClient, dataset_id: str) -> DatasetVersionResponse:
    """
    The platform's one full pipeline orchestration (docs/DECISIONS.md
    AD-12): closes the dataset's current draft into a real numbered
    version, then drives every existing analysis stage
    (enrichment -> anomaly detection -> incident correlation -> root
    cause -> business impact, which itself still fans out to
    recommendation/evaluation via the existing event publisher)
    end-to-end, scoped to this one dataset, and marks the version's real
    outcome. No stage here is new intelligence -- every one already
    existed as a real, previously-manual, per-service API call; this
    only adds the missing coordination and dataset scope.

    Synchronous by construction, matching the codebase's existing
    all-synchronous convention (no task queue exists anywhere in this
    platform, and none is introduced here) -- the HTTP request this
    Gateway route handles is held open until the whole pipeline finishes
    or fails. Acceptable at this platform's prototype scale; documented
    as a known limitation for very large datasets.

    Every stage failure is real and visible: the version is marked
    FAILED with a genuine `failure_reason`, never silently swallowed
    into a fabricated READY state.
    """
    version = await finalize_dataset_version(client, dataset_id)
    version_id = version.id

    try:
        await _set_version_status(client, dataset_id, version_id, "processing")
        await _enrich_new_complaints(client, dataset_id, version_id)

        await _set_version_status(client, dataset_id, version_id, "analyzing")
        await _run_anomaly_detection(client, dataset_id, version_id)
        await _run_incident_correlation(client, dataset_id, version_id)

        open_incidents = await _fetch_open_incidents(client, dataset_id)
        failures: List[str] = []
        for incident in open_incidents:
            incident_id = incident["id"]
            try:
                await _ensure_root_cause(client, dataset_id, version_id, incident_id)
                await _ensure_business_impact(client, dataset_id, version_id, incident_id)
            except DownstreamServiceError as exc:
                failures.append(f"Incident {incident_id}: {exc.message}")

        final_status = "partially_completed" if failures else "ready"
        failure_reason = "; ".join(failures) if failures else None
        return await _set_version_status(client, dataset_id, version_id, final_status, failure_reason=failure_reason)
    except DownstreamServiceError as exc:
        return await _set_version_status(client, dataset_id, version_id, "failed", failure_reason=exc.message)


async def _enrich_new_complaints(client: httpx.AsyncClient, dataset_id: str, version_id: str) -> None:
    """
    Enriches every complaint currently in the dataset -- not only the
    ones this version's finalize() added. nlp_service's own `POST
    /enrichments/process` is idempotent (returns the existing enrichment
    if one already exists), so re-processing an already-enriched
    complaint is a safe no-op; scanning the whole dataset (rather than
    tracking a precise "added by this version" set) keeps this
    orchestration simple and self-healing if an earlier run's enrichment
    step ever failed partway through.
    """
    complaints = await _fetch_all_complaints(client, dataset_id)
    for complaint in complaints:
        payload = {"complaint_id": complaint["id"], "text": complaint["complaint_text"]}
        response = await post_resource(client, f"{settings.NLP_SERVICE_URL}/api/v1/enrichments/process", json=payload)
        if response.status_code >= 400:
            raise DownstreamServiceError(
                f"NLP enrichment failed for complaint {complaint['id']} (status {response.status_code})."
            )


async def _fetch_all_complaints(client: httpx.AsyncClient, dataset_id: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    skip = 0
    limit = 500
    while True:
        payload = await get_json(
            client, _INGESTION_COMPLAINTS_URL, params={"dataset_id": dataset_id, "skip": skip, "limit": limit}
        )
        batch = (payload or {}).get("items", [])
        items.extend(batch)
        if len(batch) < limit:
            break
        skip += limit
    return items


async def _run_anomaly_detection(client: httpx.AsyncClient, dataset_id: str, version_id: str) -> None:
    # anomalies/run takes its parameters as query params, not a JSON body --
    # appended to the URL so post_resource still owns correlation headers
    # and timeout/connection-error translation, same as every other
    # downstream call in this module.
    url = httpx.URL(f"{settings.ANOMALY_SERVICE_URL}/api/v1/anomalies/run").copy_merge_params(
        {"dataset_id": dataset_id, "dataset_version_id": version_id, "days": str(_ENRICH_DAYS_WINDOW)}
    )
    response = await post_resource(client, str(url))
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Anomaly detection failed (status {response.status_code}).")


async def _run_incident_correlation(client: httpx.AsyncClient, dataset_id: str, version_id: str) -> None:
    url = httpx.URL(f"{settings.ANOMALY_SERVICE_URL}/api/v1/incidents/run").copy_merge_params(
        {
            "dataset_id": dataset_id,
            "dataset_version_id": version_id,
            "window_minutes": str(_CORRELATION_WINDOW_MINUTES),
        }
    )
    response = await post_resource(client, str(url))
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Incident correlation failed (status {response.status_code}).")


async def _fetch_open_incidents(client: httpx.AsyncClient, dataset_id: str) -> List[Dict[str, Any]]:
    incidents = await get_json(
        client, f"{settings.ANOMALY_SERVICE_URL}/api/v1/incidents", params={"dataset_id": dataset_id}
    )
    return incidents or []


async def _ensure_root_cause(client: httpx.AsyncClient, dataset_id: str, version_id: str, incident_id: str) -> None:
    """A 409 (a RootCause already exists for this incident) is expected on a re-run and is never treated as a failure -- it protects any human confirm/reject decision already recorded."""
    response = await post_resource(
        client,
        f"{settings.ROOT_CAUSE_SERVICE_URL}/api/v1/root-causes",
        json={"incident_id": incident_id, "dataset_id": dataset_id, "dataset_version_id": version_id},
    )
    if response.status_code == 409:
        return
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Root cause analysis failed for incident {incident_id} (status {response.status_code}).")


async def _ensure_business_impact(client: httpx.AsyncClient, dataset_id: str, version_id: str, incident_id: str) -> None:
    response = await post_resource(
        client,
        f"{settings.BUSINESS_IMPACT_SERVICE_URL}/api/v1/business-impact",
        json={"incident_id": incident_id, "dataset_id": dataset_id, "dataset_version_id": version_id},
    )
    if response.status_code >= 400:
        raise DownstreamServiceError(
            f"Business impact assessment failed for incident {incident_id} (status {response.status_code})."
        )


async def _set_version_status(
    client: httpx.AsyncClient, dataset_id: str, version_id: str, status_value: str, *, failure_reason: str | None = None
) -> DatasetVersionResponse:
    body: Dict[str, Any] = {"status": status_value}
    if failure_reason is not None:
        body["failure_reason"] = failure_reason
    raw = await patch_json(client, f"{_INGESTION_DATASETS_URL}/{dataset_id}/versions/{version_id}/status", json=body)
    if raw is None:
        raise DownstreamServiceError(f"Dataset version {version_id} was not found while updating status.")
    return to_version_response(raw)
