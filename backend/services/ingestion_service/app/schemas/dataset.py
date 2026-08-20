import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.shared.constants.enums.dataset import DatasetVersionStatus


class DatasetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None)


class DatasetResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    created_by: Optional[uuid.UUID]
    is_deleted: bool
    inserted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetVersionResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    version_number: int
    status: DatasetVersionStatus
    cumulative_record_count: int
    new_record_count: int
    analysis_started_at: Optional[datetime]
    analysis_completed_at: Optional[datetime]
    failure_reason: Optional[str]
    inserted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetVersionListResponse(BaseModel):
    items: List[DatasetVersionResponse]


class DatasetVersionStatusUpdateRequest(BaseModel):
    """
    Internal-only progress update, called exclusively by the Gateway's
    analysis orchestrator as it drives a version through
    ingesting -> processing -> analyzing -> ready/failed/partially_completed.
    Never called directly by a frontend client.
    """

    status: DatasetVersionStatus
    failure_reason: Optional[str] = None
