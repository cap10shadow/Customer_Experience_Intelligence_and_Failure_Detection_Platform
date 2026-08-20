import asyncio
from typing import Any, Dict, List, Optional

import httpx

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import get_json, post_resource
from backend.services.gateway_service.app.core.errors import (
    ConflictError,
    DownstreamServiceError,
    ResourceNotFoundError,
)
from backend.services.gateway_service.app.schemas.dataset import (
    DatasetCreateRequest,
    DatasetDetailResponse,
    DatasetResponse,
    DatasetSummaryResponse,
    DatasetVersionListResponse,
    DatasetVersionResponse,
)
from backend.shared.constants.seed_ids import LEGACY_DATASET_ID

# ingestion_service mounts its datasets router at the application root
# (app.include_router(datasets_router), no prefix) -- same reason
# ingestion_proxy.py's _COMPLAINTS_URL has no /api/v1 segment.
_DATASETS_URL = f"{settings.INGESTION_SERVICE_URL}/datasets"


async def create_dataset(client: httpx.AsyncClient, request: DatasetCreateRequest) -> DatasetResponse:
    response = await post_resource(client, _DATASETS_URL, json=request.model_dump(exclude_none=True))
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return _to_dataset_response(response.json())


async def list_datasets(client: httpx.AsyncClient) -> List[DatasetSummaryResponse]:
    """
    One real Gateway aggregation per dataset (versions + open incident
    count), mirroring investigation_aggregator's established pattern of
    stitching several services' real data into one read model -- never a
    fabricated summary. Acceptable N+1 fan-out at this platform's
    prototype scale (a handful of datasets, not thousands).
    """
    raw_datasets = await get_json(client, _DATASETS_URL)
    raw_datasets = raw_datasets or []

    async def _summarize(raw: Dict[str, Any]) -> DatasetSummaryResponse:
        dataset_id = str(raw["id"])
        versions_task = asyncio.create_task(_fetch_versions(client, dataset_id))
        incidents_task = asyncio.create_task(_fetch_open_incident_count(client, dataset_id))
        versions = await versions_task
        open_incident_count = await incidents_task
        current_version = _current_ready_version(versions)
        latest_version = versions[0] if versions else None
        return DatasetSummaryResponse(
            id=dataset_id,
            name=raw["name"],
            description=raw.get("description"),
            insertedAt=str(raw["inserted_at"]),
            isLegacy=dataset_id == str(LEGACY_DATASET_ID),
            currentVersion=current_version,
            latestVersion=latest_version,
            openIncidentCount=open_incident_count,
        )

    return list(await asyncio.gather(*(_summarize(raw) for raw in raw_datasets)))


async def get_dataset(client: httpx.AsyncClient, dataset_id: str) -> DatasetDetailResponse:
    raw = await get_json(client, f"{_DATASETS_URL}/{dataset_id}")
    if raw is None:
        raise ResourceNotFoundError(f"Dataset {dataset_id} was not found.", details={"datasetId": dataset_id})
    versions = await _fetch_versions(client, dataset_id)
    return DatasetDetailResponse(
        dataset=_to_dataset_response(raw),
        versions=versions,
        currentVersion=_current_ready_version(versions),
        latestVersion=versions[0] if versions else None,
    )


async def list_dataset_versions(client: httpx.AsyncClient, dataset_id: str) -> DatasetVersionListResponse:
    versions = await _fetch_versions(client, dataset_id)
    return DatasetVersionListResponse(items=versions)


async def get_dataset_version(client: httpx.AsyncClient, dataset_id: str, version_id: str) -> DatasetVersionResponse:
    raw = await get_json(client, f"{_DATASETS_URL}/{dataset_id}/versions/{version_id}")
    if raw is None:
        raise ResourceNotFoundError(
            f"Version {version_id} of dataset {dataset_id} was not found.",
            details={"datasetId": dataset_id, "versionId": version_id},
        )
    return to_version_response(raw)


async def archive_dataset(client: httpx.AsyncClient, dataset_id: str) -> DatasetResponse:
    response = await post_resource(client, f"{_DATASETS_URL}/{dataset_id}/archive")
    if response.status_code == 404:
        raise ResourceNotFoundError(f"Dataset {dataset_id} was not found.", details={"datasetId": dataset_id})
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return _to_dataset_response(response.json())


async def finalize_dataset_version(client: httpx.AsyncClient, dataset_id: str) -> DatasetVersionResponse:
    response = await post_resource(client, f"{_DATASETS_URL}/{dataset_id}/versions/finalize")
    if response.status_code == 404:
        raise ResourceNotFoundError(f"Dataset {dataset_id} was not found.", details={"datasetId": dataset_id})
    if response.status_code == 409:
        raise ConflictError(
            "This dataset has no open draft version to finalize -- its current version is already processing or analyzing.",
            details={"datasetId": dataset_id},
        )
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return to_version_response(response.json())


async def _fetch_versions(client: httpx.AsyncClient, dataset_id: str) -> List[DatasetVersionResponse]:
    payload = await get_json(client, f"{_DATASETS_URL}/{dataset_id}/versions")
    items = (payload or {}).get("items", [])
    return [to_version_response(item) for item in items]


async def _fetch_open_incident_count(client: httpx.AsyncClient, dataset_id: str) -> Optional[int]:
    """Non-essential: an unreachable anomaly_service degrades this summary field to None rather than failing the whole dataset list."""
    incidents = await get_json(
        client, f"{settings.ANOMALY_SERVICE_URL}/api/v1/incidents", params={"dataset_id": dataset_id}
    )
    return len(incidents) if incidents is not None else None


def _current_ready_version(versions: List[DatasetVersionResponse]) -> Optional[DatasetVersionResponse]:
    ready_versions = [v for v in versions if v.status == "ready"]
    if not ready_versions:
        return None
    return max(ready_versions, key=lambda v: v.versionNumber)


def _to_dataset_response(raw: Dict[str, Any]) -> DatasetResponse:
    dataset_id = str(raw["id"])
    return DatasetResponse(
        id=dataset_id,
        name=raw["name"],
        description=raw.get("description"),
        insertedAt=str(raw["inserted_at"]),
        isLegacy=dataset_id == str(LEGACY_DATASET_ID),
    )


def to_version_response(raw: Dict[str, Any]) -> DatasetVersionResponse:
    return DatasetVersionResponse(
        id=str(raw["id"]),
        datasetId=str(raw["dataset_id"]),
        versionNumber=raw["version_number"],
        status=str(raw["status"]),
        cumulativeRecordCount=raw["cumulative_record_count"],
        newRecordCount=raw["new_record_count"],
        analysisStartedAt=str(raw["analysis_started_at"]) if raw.get("analysis_started_at") else None,
        analysisCompletedAt=str(raw["analysis_completed_at"]) if raw.get("analysis_completed_at") else None,
        failureReason=raw.get("failure_reason"),
        insertedAt=str(raw["inserted_at"]),
    )
