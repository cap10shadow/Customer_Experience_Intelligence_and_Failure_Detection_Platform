import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from backend.services.ingestion_service.app.dependencies.repositories import ComplaintRepo
from backend.services.ingestion_service.app.models.complaint import Complaint
from backend.services.ingestion_service.app.schemas.complaint import (
    ComplaintCreateRequest,
    ComplaintListResponse,
    ComplaintResponse,
)
from backend.services.ingestion_service.app.utils.hash_helper import generate_complaint_hash
from backend.shared.constants.enums.business_impact import OperationalArea
from backend.shared.constants.enums.complaint import ComplaintStatus, SourceChannel
from backend.shared.constants.enums.enrichment import ProcessingStage

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new complaint",
    description=(
        "Ingests a complaint payload. Defaults status to INGESTED and stage to RAW_INGESTION. "
        "Will return 409 Conflict if a deduplication hash collision occurs."
    )
)
async def create_complaint(
    payload: ComplaintCreateRequest,
    repo: ComplaintRepo,
):
    # 1. Deduplication Strategy
    record_hash = generate_complaint_hash(payload.external_reference_id, payload.complaint_text)
    if await repo.exists_by_source_record_hash(record_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A complaint with this signature already exists."
        )

    # 2. Entity Mapping (Operational defaults applied)
    new_complaint = Complaint(
        **payload.model_dump(),
        complaint_status=ComplaintStatus.INGESTED,
        processing_stage=ProcessingStage.RAW_INGESTION,
        source_record_hash=record_hash,
    )

    # 3. Persistence
    created_complaint = await repo.create_complaint(new_complaint)
    
    return created_complaint


@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Get a complaint by ID"
)
async def get_complaint_by_id(
    complaint_id: uuid.UUID,
    repo: ComplaintRepo,
):
    complaint = await repo.get_by_id(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found or has been deleted."
        )
    return complaint


@router.get(
    "",
    response_model=ComplaintListResponse,
    summary="List and filter complaints"
)
async def list_complaints(
    repo: ComplaintRepo,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    complaint_status: Optional[ComplaintStatus] = Query(None),
    processing_stage: Optional[ProcessingStage] = Query(None),
    operational_area: Optional[OperationalArea] = Query(None),
    source_channel: Optional[SourceChannel] = Query(None),
    customer_region: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    # Retrieve paginated items
    items = await repo.list_complaints(
        skip=skip,
        limit=limit,
        status=complaint_status,
        stage=processing_stage,
        area=operational_area,
        channel=source_channel,
        region=customer_region,
        start_date=start_date,
        end_date=end_date,
    )
    
    # Retrieve total count for metadata
    total_count = await repo.count_complaints(
        status=complaint_status,
        stage=processing_stage,
        area=operational_area,
        channel=source_channel,
        region=customer_region,
        start_date=start_date,
        end_date=end_date,
    )

    return ComplaintListResponse(
        items=items,
        total_count=total_count,
        skip=skip,
        limit=limit
    )
