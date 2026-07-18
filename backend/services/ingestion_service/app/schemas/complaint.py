import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field

from backend.shared.constants.enums.business_impact import OperationalArea, ServiceType
from backend.shared.constants.enums.complaint import (
    ComplaintStatus,
    CustomerSegment,
    CustomerType,
    SourceChannel,
)
from backend.shared.constants.enums.enrichment import ProcessingStage


class ComplaintCreateRequest(BaseModel):
    """
    Strict payload for creating a new complaint.
    Enforces required fields and ensures payload isn't empty.
    """
    complaint_text: str = Field(..., min_length=10, description="The core text of the complaint.")
    
    # Optional context
    external_reference_id: Optional[str] = Field(None, description="External system ID for mapping.")
    complaint_title: Optional[str] = Field(None)
    complaint_source: Optional[str] = Field(None)
    source_channel: Optional[SourceChannel] = Field(None)
    
    # Customer
    customer_region: Optional[str] = Field(None)
    customer_segment: Optional[CustomerSegment] = Field(None)
    customer_type: Optional[CustomerType] = Field(None)
    
    # Operational
    product_category: Optional[str] = Field(None)
    operational_area: Optional[OperationalArea] = Field(None)
    service_type: Optional[ServiceType] = Field(None)
    
    # Temporal
    event_occurred_at: Optional[datetime] = Field(None, description="Timezone-aware occurrence timestamp.")


class ComplaintResponse(BaseModel):
    """
    Output serialization mapped strictly to the SQLAlchemy ORM model.
    """
    id: uuid.UUID
    inserted_at: datetime
    
    external_reference_id: Optional[str]
    complaint_title: Optional[str]
    complaint_text: str
    complaint_source: Optional[str]
    source_channel: Optional[SourceChannel]
    
    normalized_title: Optional[str]
    normalized_complaint_text: Optional[str]
    
    customer_region: Optional[str]
    customer_segment: Optional[CustomerSegment]
    customer_type: Optional[CustomerType]
    
    product_category: Optional[str]
    operational_area: Optional[OperationalArea]
    service_type: Optional[ServiceType]
    
    event_occurred_at: Optional[datetime]
    
    complaint_status: ComplaintStatus
    processing_stage: ProcessingStage
    is_deleted: bool
    
    ingestion_source: Optional[str]
    ingestion_batch_id: Optional[str]
    source_record_hash: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ComplaintListResponse(BaseModel):
    """
    Lightweight paginated response structure.
    """
    items: List[ComplaintResponse]
    total_count: int
    skip: int
    limit: int
