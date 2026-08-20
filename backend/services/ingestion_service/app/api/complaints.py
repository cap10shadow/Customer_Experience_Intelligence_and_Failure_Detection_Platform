import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from backend.services.ingestion_service.app.dependencies.repositories import ComplaintRepo, DatasetRepo
from backend.services.ingestion_service.app.repositories.complaint_repository import DuplicateRecordError
from backend.services.ingestion_service.app.dependencies.services import MappingSvc
from backend.services.ingestion_service.app.models.complaint import Complaint
from backend.services.ingestion_service.app.schemas.complaint import (
    ComplaintCreateRequest,
    ComplaintListResponse,
    ComplaintResponse,
)
from backend.services.ingestion_service.app.schemas.complaint_analysis import (
    AnalyzeRowInput,
    BatchRowOutcome,
    ComplaintAnalyzeRequest,
    ComplaintAnalyzeResponse,
    ComplaintBatchRequest,
    ComplaintBatchResponse,
    RowAnalysisResult,
)
from backend.services.ingestion_service.app.services.row_analysis import analyze_rows
from backend.services.ingestion_service.app.utils.hash_helper import generate_complaint_hash
from backend.shared.constants.enums.business_impact import OperationalArea, ServiceType
from backend.shared.constants.enums.complaint import ComplaintStatus, CustomerSegment, CustomerType, SourceChannel
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
    dataset_repo: DatasetRepo,
    dataset_id: uuid.UUID = Query(..., description="The Dataset this complaint belongs to."),
):
    # 0. Resolve the dataset's currently-open draft version -- a complaint
    # can only ever be ingested into a DRAFT version; if the dataset's
    # draft has already been finalized (or the dataset doesn't exist),
    # there is nowhere real to put this record.
    dataset = await dataset_repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    draft = await dataset_repo.get_draft_version(dataset_id)
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This dataset has no open draft version to ingest into -- its current version is already finalized.",
        )

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
        dataset_id=dataset_id,
        dataset_version_id=draft.id,
        complaint_status=ComplaintStatus.INGESTED,
        processing_stage=ProcessingStage.RAW_INGESTION,
        source_record_hash=record_hash,
    )

    # 3. Persistence -- DuplicateRecordError is the database-level backstop
    # behind the exists_by_source_record_hash check above, for a concurrent
    # or retried request that committed in between.
    try:
        created_complaint = await repo.create_complaint(new_complaint)
    except DuplicateRecordError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A complaint with this signature already exists.",
        )

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
    dataset_id: Optional[uuid.UUID] = Query(None),
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
        dataset_id=dataset_id,
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
        dataset_id=dataset_id,
    )

    return ComplaintListResponse(
        items=items,
        total_count=total_count,
        skip=skip,
        limit=limit
    )


@router.post(
    ":analyze",
    response_model=ComplaintAnalyzeResponse,
    summary="Classify a batch of client-parsed rows -- normalization, mapping, validation. Persists no Complaint rows.",
    description=(
        "The backend, not the frontend, owns normalization/mapping/validation. Classifies "
        "customer_region/operational_area against approved mappings, the curated alias-suggestion "
        "registry, and enum membership, processing each DISTINCT value once regardless of row count. "
        "Never persists a Complaint row; only ever creates/refreshes PENDING FieldValueMapping rows."
    ),
)
async def analyze_complaints(
    payload: ComplaintAnalyzeRequest,
    mapping_service: MappingSvc,
    dataset_repo: DatasetRepo,
    dataset_id: uuid.UUID = Query(..., description="The Dataset this analysis belongs to."),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=500),
):
    dataset = await dataset_repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    results, summary, pending_clusters = await analyze_rows(
        payload.rows, mapping_service, payload.analysis_session_id, dataset_id
    )

    total_rows = len(results)
    start = (page - 1) * page_size
    page_results = results[start : start + page_size]
    total_pages = max(1, -(-total_rows // page_size))

    return ComplaintAnalyzeResponse(
        dataset_id=dataset_id,
        total_rows=total_rows,
        summary=summary,
        pending_clusters=pending_clusters,
        results=page_results,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    ":batch",
    response_model=ComplaintBatchResponse,
    summary="Submit a batch of rows in one transaction, using currently-approved mappings.",
    description=(
        "Re-classifies every row against the CURRENT mapping/registry state (so approvals made "
        "between :analyze and :batch are honored), rejects any row still needs-mapping/structurally "
        "invalid with a stated reason -- never guesses -- and accounts for every row in the response: "
        "len(outcomes) always equals len(rows)."
    ),
)
async def batch_submit_complaints(
    payload: ComplaintBatchRequest,
    mapping_service: MappingSvc,
    dataset_repo: DatasetRepo,
    repo: ComplaintRepo,
    dataset_id: uuid.UUID = Query(..., description="The Dataset this batch belongs to."),
):
    dataset = await dataset_repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    draft = await dataset_repo.get_draft_version(dataset_id)
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This dataset has no open draft version to ingest into -- its current version is already finalized.",
        )

    results, _summary, _clusters = await analyze_rows(
        payload.rows, mapping_service, payload.analysis_session_id, dataset_id
    )
    results_by_row = {r.row_number: r for r in results}
    rows_by_number = {r.row_number: r for r in payload.rows}

    # Hashes for every structurally-acceptable row, computed up front -- one bulk
    # dedup query below instead of N sequential ones.
    hashes_by_row: dict[int, str] = {
        row_number: generate_complaint_hash(rows_by_number[row_number].external_reference_id, rows_by_number[row_number].complaint_text)
        for row_number, result in results_by_row.items()
        if result.status in ("accepted", "auto_normalized")
    }
    existing_hashes = await repo.bulk_exists_by_source_record_hash(list(hashes_by_row.values()))
    seen_in_batch: set[str] = set()

    outcomes: list[BatchRowOutcome] = []
    to_create: list[Complaint] = []

    for row_number in sorted(results_by_row.keys()):
        result = results_by_row[row_number]
        row = rows_by_number[row_number]

        if result.status not in ("accepted", "auto_normalized"):
            reason = "; ".join(f"{issue.field}: {issue.problem}" for issue in result.issues) or "row rejected"
            outcomes.append(
                BatchRowOutcome(row_number=row_number, outcome="rejected", reason=reason, source_file_name=row.source_file_name)
            )
            continue

        record_hash = hashes_by_row[row_number]
        if record_hash in existing_hashes:
            outcomes.append(
                BatchRowOutcome(
                    row_number=row_number,
                    outcome="duplicate",
                    reason="duplicate of existing complaint",
                    source_file_name=row.source_file_name,
                )
            )
            continue
        if record_hash in seen_in_batch:
            outcomes.append(
                BatchRowOutcome(
                    row_number=row_number,
                    outcome="duplicate",
                    reason="duplicate within this upload",
                    source_file_name=row.source_file_name,
                )
            )
            continue
        seen_in_batch.add(record_hash)

        complaint = _build_complaint(row, result, dataset_id, draft.id, record_hash)
        to_create.append(complaint)
        outcomes.append(
            BatchRowOutcome(row_number=row_number, outcome="created", complaint_id=complaint.id, source_file_name=row.source_file_name)
        )

    persisted_ids: set[uuid.UUID] = await repo.create_complaints_bulk(to_create) if to_create else set()

    # Any complaint queued as "created" above whose id did NOT make it into
    # persisted_ids lost a concurrent/retried-request race for the same
    # hash after our own bulk_exists_by_source_record_hash check -- the
    # unique constraint (DB-level backstop) is what actually caught it.
    # Reclassify its outcome so the response stays honest instead of
    # claiming a row was created that the database rejected.
    if len(persisted_ids) != len(to_create):
        lost_ids = {c.id for c in to_create} - persisted_ids
        outcomes = [
            BatchRowOutcome(
                row_number=o.row_number,
                outcome="duplicate",
                reason="duplicate of existing complaint (concurrent insert)",
                source_file_name=o.source_file_name,
            )
            if o.complaint_id in lost_ids
            else o
            for o in outcomes
        ]

    assert len(outcomes) == len(payload.rows), "zero-loss invariant violated: every row must produce exactly one outcome"

    created_count = sum(1 for o in outcomes if o.outcome == "created")
    duplicate_count = sum(1 for o in outcomes if o.outcome == "duplicate")
    rejected_count = sum(1 for o in outcomes if o.outcome == "rejected")

    return ComplaintBatchResponse(
        dataset_id=dataset_id,
        dataset_version_id=draft.id,
        total_rows=len(payload.rows),
        created_count=created_count,
        duplicate_count=duplicate_count,
        rejected_count=rejected_count,
        outcomes=outcomes,
    )


def _build_complaint(
    row: AnalyzeRowInput,
    result: RowAnalysisResult,
    dataset_id: uuid.UUID,
    dataset_version_id: uuid.UUID,
    record_hash: str,
) -> Complaint:
    """
    Builds the ORM Complaint from a row + its analysis result's
    normalized_preview -- customer_region/operational_area get the
    CANONICAL value (preview[field]); the as-typed original is preserved
    separately in raw_customer_region/raw_operational_area, never
    overwritten. `id` is set explicitly (not left to the column default)
    so it's known before flush, for the outcome's complaint_id.
    """
    preview = result.normalized_preview
    return Complaint(
        id=uuid.uuid4(),
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
        external_reference_id=row.external_reference_id,
        complaint_title=row.complaint_title,
        complaint_text=row.complaint_text,
        complaint_source=row.complaint_source,
        source_channel=SourceChannel(preview["source_channel"]) if "source_channel" in preview else None,
        customer_region=preview.get("customer_region"),
        raw_customer_region=row.customer_region,
        customer_segment=CustomerSegment(preview["customer_segment"]) if "customer_segment" in preview else None,
        customer_type=CustomerType(preview["customer_type"]) if "customer_type" in preview else None,
        product_category=row.product_category,
        operational_area=OperationalArea(preview["operational_area"]) if "operational_area" in preview else None,
        raw_operational_area=row.operational_area,
        service_type=ServiceType(preview["service_type"]) if "service_type" in preview else None,
        event_occurred_at=datetime.fromisoformat(preview["event_occurred_at"]) if "event_occurred_at" in preview else None,
        complaint_status=ComplaintStatus.INGESTED,
        processing_stage=ProcessingStage.RAW_INGESTION,
        source_record_hash=record_hash,
    )
