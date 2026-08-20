from typing import List, Optional

from pydantic import BaseModel, Field


class IngestionComplaintRequest(BaseModel):
    """
    Public request body for `POST /api/v1/ingestion/complaints`, mirroring
    ingestion_service's own `ComplaintCreateRequest` field-for-field.
    Enum-typed fields (source_channel/customer_segment/customer_type/
    operational_area/service_type) are kept as plain `str` here rather
    than importing ingestion_service's domain enums -- DATA-002, the same
    convention `schemas/recommendations.py`'s `RecommendationDecisionValue`
    documents. ingestion_service still validates them for real; an invalid
    value is forwarded and rejected downstream (see `ingestion_proxy.
    create_complaint`), never re-validated here against a duplicated enum.
    """

    complaint_text: str = Field(..., min_length=10)
    external_reference_id: Optional[str] = None
    complaint_title: Optional[str] = None
    complaint_source: Optional[str] = None
    source_channel: Optional[str] = None
    customer_region: Optional[str] = None
    customer_segment: Optional[str] = None
    customer_type: Optional[str] = None
    product_category: Optional[str] = None
    operational_area: Optional[str] = None
    service_type: Optional[str] = None
    event_occurred_at: Optional[str] = None


class IngestionComplaintResponse(BaseModel):
    """
    Public read model for one ingested complaint. Every field maps 1:1 to
    a real ingestion_service field (`ComplaintResponse`) -- no field is
    added or fabricated here.
    """

    id: str
    datasetId: str
    complaintText: str
    complaintTitle: Optional[str] = None
    externalReferenceId: Optional[str] = None
    complaintSource: Optional[str] = None
    sourceChannel: Optional[str] = None
    customerRegion: Optional[str] = None
    productCategory: Optional[str] = None
    operationalArea: Optional[str] = None
    complaintStatus: str
    processingStage: str
    insertedAt: str


class IngestionComplaintListResponse(BaseModel):
    items: List[IngestionComplaintResponse]
    totalCount: int
    skip: int
    limit: int
