from typing import List, Optional

from pydantic import BaseModel, Field


class DatasetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class DatasetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    insertedAt: str
    isLegacy: bool = False


class DatasetVersionResponse(BaseModel):
    """Mirrors ingestion_service's DatasetVersionResponse -- a real, finalized snapshot marker, never a fabricated progress percentage."""

    id: str
    datasetId: str
    versionNumber: int
    status: str
    cumulativeRecordCount: int
    newRecordCount: int
    analysisStartedAt: Optional[str] = None
    analysisCompletedAt: Optional[str] = None
    failureReason: Optional[str] = None
    insertedAt: str


class DatasetVersionListResponse(BaseModel):
    items: List[DatasetVersionResponse]


class DatasetSummaryResponse(BaseModel):
    """
    The Data workspace's dataset list-card view: real counts, never
    estimated. `currentVersion` is the highest READY version (what
    Dashboard/Analytics would show if this dataset were selected);
    `latestVersion` may be a still-processing/failed version ahead of it
    -- both are surfaced so the UI can show "new data processing" instead
    of silently presenting the last completed analysis as if it were current.
    """

    id: str
    name: str
    description: Optional[str] = None
    insertedAt: str
    isLegacy: bool = False
    currentVersion: Optional[DatasetVersionResponse] = None
    latestVersion: Optional[DatasetVersionResponse] = None
    openIncidentCount: Optional[int] = None


class DatasetDetailResponse(BaseModel):
    """`latestVersion` mirrors `DatasetSummaryResponse`'s existing distinction: the most recent version regardless of status (what the Data workspace's badge/history should reflect), vs `currentVersion`, the highest READY version (what Dashboard/Analytics would show)."""

    dataset: DatasetResponse
    versions: List[DatasetVersionResponse]
    currentVersion: Optional[DatasetVersionResponse] = None
    latestVersion: Optional[DatasetVersionResponse] = None
