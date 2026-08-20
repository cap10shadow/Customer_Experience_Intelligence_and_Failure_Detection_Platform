import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.shared.constants.enums.field_mapping import (
    FieldValueMappingConfidence,
    FieldValueMappingStatus,
    FieldValueMappingType,
)


class FieldValueMappingResponse(BaseModel):
    id: uuid.UUID
    field_name: str
    raw_value_normalized: str
    raw_value_original_example: str
    target_value: Optional[str]
    suggested_target_value: Optional[str]
    confidence: FieldValueMappingConfidence
    mapping_type: Optional[FieldValueMappingType]
    status: FieldValueMappingStatus
    occurrence_count: int
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    inserted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FieldValueMappingListResponse(BaseModel):
    items: List[FieldValueMappingResponse]
    total_count: int
    skip: int
    limit: int


class ApproveMappingRequest(BaseModel):
    target_value: str = Field(..., min_length=1)
    reviewed_by: Optional[str] = None


class BulkApproveMappingRequest(BaseModel):
    mapping_ids: List[uuid.UUID] = Field(..., min_length=1)
    target_value: str = Field(..., min_length=1)
    reviewed_by: Optional[str] = None


class BulkApproveMappingResponse(BaseModel):
    approved: List[FieldValueMappingResponse]


class RejectMappingRequest(BaseModel):
    reviewed_by: Optional[str] = None


class AliasSuggestionCreateRequest(BaseModel):
    field_name: str = Field(..., min_length=1)
    source_value: str = Field(..., min_length=1)
    suggested_target_value: str = Field(..., min_length=1)
    notes: Optional[str] = None
    created_by: Optional[str] = None


class AliasSuggestionUpdateRequest(BaseModel):
    suggested_target_value: str = Field(..., min_length=1)


class AliasSuggestionResponse(BaseModel):
    id: uuid.UUID
    field_name: str
    source_value_normalized: str
    suggested_target_value: str
    notes: Optional[str]
    created_by: Optional[str]
    inserted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AliasSuggestionListResponse(BaseModel):
    items: List[AliasSuggestionResponse]
