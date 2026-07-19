import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response

from backend.services.nlp_service.app.dependencies.services import (
    get_enrichment_repository,
    get_enrichment_service,
)
from backend.services.nlp_service.app.repositories.complaint_enrichment_repository import EnrichmentRepository
from backend.services.nlp_service.app.services.enrichment_service import EnrichmentService
from backend.services.nlp_service.app.schemas.complaint_enrichment import (
    ComplaintEnrichmentListResponse,
    ComplaintEnrichmentResponse,
    ProcessEnrichmentRequest,
)
from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel


router = APIRouter(prefix="/enrichments", tags=["enrichments"])


@router.post(
    "/process",
    response_model=ComplaintEnrichmentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        201: {"description": "Enrichment successfully processed and created."},
        200: {"description": "Enrichment already exists for this complaint."},
    },
)
async def process_enrichment(
    request: ProcessEnrichmentRequest,
    response: Response,
    service: EnrichmentService = Depends(get_enrichment_service),
    repository: EnrichmentRepository = Depends(get_enrichment_repository),
):
    """
    Process a complaint's text through the NLP enrichment pipeline.
    
    If the enrichment already exists, returns the existing record (idempotent).
    The force_reprocess flag is currently reserved for future use.
    """
    enrichment = await service.enrich_complaint(
        complaint_id=request.complaint_id, text=request.text
    )

    if enrichment is None:
        # It already exists
        existing = await repository.get_by_complaint_id(request.complaint_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrichment expected but not found.",
            )
        return existing
        
    response.status_code = status.HTTP_201_CREATED
    return enrichment


@router.get(
    "/{enrichment_id}",
    response_model=ComplaintEnrichmentResponse,
)
async def get_enrichment(
    enrichment_id: uuid.UUID,
    repository: EnrichmentRepository = Depends(get_enrichment_repository),
):
    """Retrieve an enrichment by its ID."""
    enrichment = await repository.get_by_id(enrichment_id)
    if not enrichment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrichment not found",
        )
    return enrichment


@router.get(
    "/by-complaint/{complaint_id}",
    response_model=ComplaintEnrichmentResponse,
)
async def get_enrichment_by_complaint(
    complaint_id: uuid.UUID,
    repository: EnrichmentRepository = Depends(get_enrichment_repository),
):
    """Retrieve an enrichment by the associated complaint ID."""
    enrichment = await repository.get_by_complaint_id(complaint_id)
    if not enrichment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrichment not found for this complaint",
        )
    return enrichment


@router.get(
    "",
    response_model=ComplaintEnrichmentListResponse,
)
async def list_enrichments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sentiment: Optional[SentimentLabel] = None,
    urgency: Optional[UrgencyLabel] = None,
    issue_category: Optional[IssueCategory] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    repository: EnrichmentRepository = Depends(get_enrichment_repository),
):
    """
    List and filter enrichments with pagination.
    """
    items = await repository.list_enrichments(
        skip=skip,
        limit=limit,
        sentiment_label=sentiment,
        urgency_label=urgency,
        issue_category=issue_category,
        start_date=start_date,
        end_date=end_date,
    )

    total = await repository.count_enrichments(
        sentiment_label=sentiment,
        urgency_label=urgency,
        issue_category=issue_category,
        start_date=start_date,
        end_date=end_date,
    )

    # Calculate current page based on skip and limit
    page = (skip // limit) + 1 if limit > 0 else 1
    
    return ComplaintEnrichmentListResponse(
        items=list(items),
        total=total,
        page=page,
        size=len(items)
    )
