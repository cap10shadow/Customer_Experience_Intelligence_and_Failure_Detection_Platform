import uuid
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AnalyzeRowInput(BaseModel):
    """
    One client-parsed CSV/JSON row, submitted as raw strings for
    server-side classification. Structurally identical to
    ComplaintCreateRequest except every field arrives untyped/unvalidated
    (including `event_occurred_at`, deliberately kept as a raw string
    rather than `datetime` -- a malformed date must become a per-row
    RowFieldIssue, not a request-level 422 that aborts the whole batch)
    -- :analyze is where validation, normalization, and mapping
    classification actually happen, replacing today's hard 422-on-first-
    bad-field behavior with a full per-row, per-field breakdown.
    """

    row_number: int = Field(..., ge=1)
    complaint_text: Optional[str] = None
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
    source_file_name: Optional[str] = Field(
        None,
        description=(
            "The upload file this row came from (client-assigned, opaque to the backend -- never "
            "used for validation/mapping). Echoed back on RowAnalysisResult/BatchRowOutcome so the "
            "client's per-file upload manifest stays correct across :analyze and :batch without "
            "re-deriving it from row_number, which is not stable across re-analyzes of a filtered set."
        ),
    )


class ComplaintAnalyzeRequest(BaseModel):
    analysis_session_id: uuid.UUID = Field(
        ...,
        description=(
            "Generated once by the client per file parse, reused across every re-analyze of the same "
            "row set. A new upload always uses a new id. Backend uses this to deduplicate occurrence "
            "contributions -- re-analyzing unchanged rows must never inflate mapping occurrence counts."
        ),
    )
    rows: List[AnalyzeRowInput] = Field(..., min_length=1, max_length=10000)


class RowFieldIssue(BaseModel):
    row_number: int
    field: str
    provided_value: str
    problem: Literal["needs_mapping", "invalid_enum", "invalid_format", "required_missing"]
    confidence: Optional[Literal["high", "medium", "low"]] = None
    suggested_target_value: Optional[str] = None
    suggested_action: Literal["accept_suggestion", "review_mapping", "fix_value", "provide_value"]


class RowAnalysisResult(BaseModel):
    row_number: int
    status: Literal["accepted", "auto_normalized", "suggested_mapping", "needs_review", "rejected"]
    issues: List[RowFieldIssue] = Field(default_factory=list)
    normalized_preview: dict = Field(default_factory=dict)
    source_file_name: Optional[str] = None


class PendingClusterSummary(BaseModel):
    field_name: str
    raw_value_normalized: str
    example_values: List[str]
    occurrence_count: int
    confidence: Literal["medium", "low"]
    suggested_target_value: Optional[str] = None
    mapping_id: uuid.UUID
    valid_choices: Optional[List[str]] = None


class ComplaintAnalyzeResponse(BaseModel):
    dataset_id: uuid.UUID
    total_rows: int
    summary: dict
    pending_clusters: List[PendingClusterSummary]
    results: List[RowAnalysisResult]
    page: int
    page_size: int
    total_pages: int


class BatchRowInput(AnalyzeRowInput):
    pass


class ComplaintBatchRequest(BaseModel):
    analysis_session_id: uuid.UUID
    rows: List[BatchRowInput] = Field(..., min_length=1, max_length=10000)


class BatchRowOutcome(BaseModel):
    row_number: int
    outcome: Literal["created", "duplicate", "rejected"]
    complaint_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
    source_file_name: Optional[str] = None


class ComplaintBatchResponse(BaseModel):
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
    total_rows: int
    created_count: int
    duplicate_count: int
    rejected_count: int
    outcomes: List[BatchRowOutcome]
