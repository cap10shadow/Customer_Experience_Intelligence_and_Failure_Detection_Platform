from typing import Any, Dict

import httpx
from fastapi import APIRouter, Body, Depends, Query, status

from backend.services.gateway_service.app.core.authorization import require_role
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.dataset import (
    DatasetCreateRequest,
    DatasetDetailResponse,
    DatasetResponse,
    DatasetSummaryResponse,
    DatasetVersionListResponse,
    DatasetVersionResponse,
)
from backend.services.gateway_service.app.schemas.ingestion import (
    IngestionComplaintListResponse,
    IngestionComplaintRequest,
    IngestionComplaintResponse,
)
from backend.services.gateway_service.app.services.dataset_analysis_orchestrator import run_analysis_for_dataset
from backend.services.gateway_service.app.services.dataset_proxy import (
    archive_dataset,
    create_dataset,
    get_dataset,
    get_dataset_version,
    list_dataset_versions,
    list_datasets,
)
from backend.services.gateway_service.app.services.ingestion_proxy import (
    analyze_complaints,
    batch_submit_complaints,
    create_complaint,
    list_complaints,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("operator"))])
async def post_dataset(
    request: DatasetCreateRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> DatasetResponse:
    """Creates a Dataset -- the top-level analytical workspace every other workspace (Dashboard, Analytics, Investigations, Recommendations) scopes itself to."""
    return await create_dataset(client, request)


@router.get("", response_model=list[DatasetSummaryResponse])
async def get_datasets(client: httpx.AsyncClient = Depends(get_http_client)) -> list[DatasetSummaryResponse]:
    return await list_datasets(client)


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
async def get_dataset_detail(dataset_id: str, client: httpx.AsyncClient = Depends(get_http_client)) -> DatasetDetailResponse:
    return await get_dataset(client, dataset_id)


@router.post(
    "/{dataset_id}/archive",
    response_model=DatasetResponse,
    dependencies=[Depends(require_role("operator"))],
)
async def post_dataset_archive(dataset_id: str, client: httpx.AsyncClient = Depends(get_http_client)) -> DatasetResponse:
    """Archives (soft-deletes) a dataset -- never a hard delete. See dataset_proxy.archive_dataset."""
    return await archive_dataset(client, dataset_id)


@router.get("/{dataset_id}/versions", response_model=DatasetVersionListResponse)
async def get_dataset_versions(dataset_id: str, client: httpx.AsyncClient = Depends(get_http_client)) -> DatasetVersionListResponse:
    return await list_dataset_versions(client, dataset_id)


@router.get("/{dataset_id}/versions/{version_id}", response_model=DatasetVersionResponse)
async def get_dataset_version_detail(
    dataset_id: str, version_id: str, client: httpx.AsyncClient = Depends(get_http_client)
) -> DatasetVersionResponse:
    """Real-time-enough polling target: the frontend polls this while a version's status is ingesting/processing/analyzing."""
    return await get_dataset_version(client, dataset_id, version_id)


@router.post(
    "/{dataset_id}/versions/finalize",
    response_model=DatasetVersionResponse,
    dependencies=[Depends(require_role("operator"))],
)
async def post_finalize_and_analyze(dataset_id: str, client: httpx.AsyncClient = Depends(get_http_client)) -> DatasetVersionResponse:
    """
    The one route that closes the dataset's current draft into a real
    version AND drives the full analysis pipeline for it (enrichment,
    anomaly detection, incident correlation, root cause, business
    impact/recommendations) before returning. Synchronous -- the
    response only comes back once the real pipeline has actually
    finished (or genuinely failed), never a fabricated "processing"
    placeholder returned early. See `dataset_analysis_orchestrator.
    run_analysis_for_dataset`'s docstring for the full sequence and its
    known scale limitation.
    """
    return await run_analysis_for_dataset(client, dataset_id)


@router.post(
    "/{dataset_id}/complaints",
    response_model=IngestionComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("operator"))],
)
async def post_dataset_complaint(
    dataset_id: str,
    request: IngestionComplaintRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> IngestionComplaintResponse:
    """Ingests one complaint into this dataset's currently-open draft version -- see ingestion_proxy.create_complaint for the real 404/409/422 cases this can surface."""
    return await create_complaint(client, dataset_id, request)


@router.get("/{dataset_id}/complaints", response_model=IngestionComplaintListResponse)
async def get_dataset_complaints(
    dataset_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> IngestionComplaintListResponse:
    return await list_complaints(client, dataset_id=dataset_id, skip=skip, limit=limit)


@router.post(
    "/{dataset_id}/complaints:analyze",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_role("operator"))],
)
async def post_dataset_complaints_analyze(
    dataset_id: str,
    request: Dict[str, Any] = Body(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=500),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> Dict[str, Any]:
    """
    Pure pass-through to ingestion_service's `POST /complaints:analyze` --
    see `ingestion_proxy.analyze_complaints` for why the payload isn't
    remapped into a Gateway-owned schema. The backend, not the Gateway,
    owns normalization/mapping/validation.
    """
    return await analyze_complaints(client, dataset_id, request, page=page, page_size=page_size)


@router.post(
    "/{dataset_id}/complaints:batch",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_role("operator"))],
)
async def post_dataset_complaints_batch(
    dataset_id: str,
    request: Dict[str, Any] = Body(...),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> Dict[str, Any]:
    """Pure pass-through to ingestion_service's `POST /complaints:batch`."""
    return await batch_submit_complaints(client, dataset_id, request)
