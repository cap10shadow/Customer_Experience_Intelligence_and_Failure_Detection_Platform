import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from backend.services.ingestion_service.app.dependencies.repositories import DatasetRepo
from backend.services.ingestion_service.app.models.dataset import Dataset, DatasetVersion
from backend.services.ingestion_service.app.schemas.dataset import (
    DatasetCreateRequest,
    DatasetResponse,
    DatasetVersionListResponse,
    DatasetVersionResponse,
    DatasetVersionStatusUpdateRequest,
)
from backend.shared.constants.enums.dataset import DatasetVersionStatus

router = APIRouter(prefix="/datasets", tags=["datasets"])

_ANALYSIS_STARTING_STATUSES = {DatasetVersionStatus.PROCESSING, DatasetVersionStatus.ANALYZING}
_ANALYSIS_TERMINAL_STATUSES = {
    DatasetVersionStatus.READY,
    DatasetVersionStatus.FAILED,
    DatasetVersionStatus.PARTIALLY_COMPLETED,
}


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(payload: DatasetCreateRequest, repo: DatasetRepo):
    """Creates a Dataset and immediately opens its first DatasetVersion (version 1, DRAFT) so ingestion has somewhere to target right away."""
    dataset = await repo.create_dataset(Dataset(name=payload.name, description=payload.description))
    await repo.create_dataset_version(
        DatasetVersion(dataset_id=dataset.id, version_number=1, status=DatasetVersionStatus.DRAFT)
    )
    return dataset


@router.get("", response_model=list[DatasetResponse])
async def list_datasets(repo: DatasetRepo):
    return await repo.list_datasets()


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: uuid.UUID, repo: DatasetRepo):
    dataset = await repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


@router.post(
    "/{dataset_id}/archive",
    response_model=DatasetResponse,
    summary="Archive (soft-delete) a dataset -- never a hard delete",
    description=(
        "Sets is_deleted = True. DatasetVersions, Complaints, and every downstream "
        "intelligence entity (anomalies, incidents, root causes, business impact, "
        "recommendations) referencing this dataset are left completely intact -- "
        "archiving only removes the dataset from listings/lookups by default, it "
        "never deletes a row or breaks a foreign key. Idempotent: archiving an "
        "already-archived (or nonexistent) dataset returns 404, since it's no "
        "longer visible to a default get_dataset lookup."
    ),
)
async def archive_dataset(dataset_id: uuid.UUID, repo: DatasetRepo):
    dataset = await repo.archive_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/versions", response_model=DatasetVersionListResponse)
async def list_dataset_versions(dataset_id: uuid.UUID, repo: DatasetRepo):
    dataset = await repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    versions = await repo.list_dataset_versions(dataset_id)
    return DatasetVersionListResponse(items=list(versions))


@router.get("/{dataset_id}/versions/{version_id}", response_model=DatasetVersionResponse)
async def get_dataset_version(dataset_id: uuid.UUID, version_id: uuid.UUID, repo: DatasetRepo):
    version = await repo.get_dataset_version(version_id)
    if version is None or version.dataset_id != dataset_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset version not found")
    return version


@router.post("/{dataset_id}/versions/finalize", response_model=DatasetVersionResponse)
async def finalize_dataset_version(dataset_id: uuid.UUID, repo: DatasetRepo):
    """
    Closes the dataset's current DRAFT version into a real, numbered
    snapshot (real record counts, computed by a genuine COUNT query --
    never estimated) and immediately opens the next DRAFT version so
    future ingestion always has somewhere to go. Does NOT run any
    analysis itself -- this service has no knowledge of NLP/anomaly/root
    cause/business impact; the Gateway's orchestrator calls this first,
    then drives the rest of the pipeline against the returned version id.
    A dataset with no complaints in its draft yet can still be finalized
    (new_record_count = 0) -- the caller decides whether that's
    meaningful, not this endpoint.
    """
    dataset = await repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    draft = await repo.get_draft_version(dataset_id)
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No draft version is open for this dataset -- it may already be processing or analyzing.",
        )

    new_count = await repo.count_complaints_in_version(draft.id)
    cumulative_count = await repo.count_complaints_in_dataset(dataset_id)

    draft.new_record_count = new_count
    draft.cumulative_record_count = cumulative_count
    draft.status = DatasetVersionStatus.INGESTING
    await repo.save_version(draft)

    next_version_number = draft.version_number + 1
    await repo.create_dataset_version(
        DatasetVersion(dataset_id=dataset_id, version_number=next_version_number, status=DatasetVersionStatus.DRAFT)
    )

    return draft


@router.patch("/{dataset_id}/versions/{version_id}/status", response_model=DatasetVersionResponse)
async def update_dataset_version_status(
    dataset_id: uuid.UUID, version_id: uuid.UUID, payload: DatasetVersionStatusUpdateRequest, repo: DatasetRepo
):
    """Internal progress endpoint the Gateway orchestrator uses to advance a version through its real pipeline stages."""
    version = await repo.get_dataset_version(version_id)
    if version is None or version.dataset_id != dataset_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset version not found")

    if payload.status in _ANALYSIS_STARTING_STATUSES and version.analysis_started_at is None:
        version.analysis_started_at = datetime.now(timezone.utc)
    if payload.status in _ANALYSIS_TERMINAL_STATUSES:
        version.analysis_completed_at = datetime.now(timezone.utc)

    version.status = payload.status
    version.failure_reason = payload.failure_reason
    await repo.save_version(version)
    return version
