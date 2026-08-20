import uuid
from datetime import datetime
from typing import Optional

from backend.services.ingestion_service.app.schemas.complaint_analysis import (
    AnalyzeRowInput,
    PendingClusterSummary,
    RowAnalysisResult,
    RowFieldIssue,
)
from backend.services.ingestion_service.app.services.mapping_service import (
    MAPPED_FIELDS,
    MappingService,
    ValueClassification,
    enum_choices_for_field,
)

_MIN_COMPLAINT_TEXT_LENGTH = 10

_STATUS_PRIORITY = {
    "rejected": 0,
    "needs_review": 1,
    "suggested_mapping": 2,
    "auto_normalized": 3,
    "accepted": 4,
}


async def analyze_rows(
    rows: list[AnalyzeRowInput],
    mapping_service: MappingService,
    analysis_session_id: uuid.UUID,
    dataset_id: uuid.UUID,
) -> tuple[list[RowAnalysisResult], dict[str, int], list[PendingClusterSummary]]:
    """
    Validates structural fields per row, classifies every MAPPED_FIELDS
    value (customer_region, operational_area, source_channel,
    customer_segment, customer_type, service_type) ACROSS THE WHOLE
    BATCH ONCE (not per row -- this is what makes a 10,000-row upload
    with 40 distinct values do O(40), not O(10,000) mapping work), then
    reassembles a per-row result plus a batch-level summary and
    pending-cluster list.
    """
    field_values: dict[str, dict[str, int]] = {field: {} for field in MAPPED_FIELDS}
    for row in rows:
        for field_name in MAPPED_FIELDS:
            value = getattr(row, field_name)
            if value is not None and value.strip():
                field_values[field_name][value] = field_values[field_name].get(value, 0) + 1

    classifications_by_field: dict[str, dict[str, object]] = {}
    for field_name, values_with_counts in field_values.items():
        classifications_by_field[field_name] = await mapping_service.classify_unique_values(
            field_name, values_with_counts, analysis_session_id, first_seen_dataset_id=dataset_id
        )

    results: list[RowAnalysisResult] = []
    summary = {"accepted": 0, "auto_normalized": 0, "suggested_mapping": 0, "needs_review": 0, "rejected": 0}
    cluster_mapping_ids: set[uuid.UUID] = set()
    cluster_examples: dict[uuid.UUID, tuple[str, str, set[str]]] = {}

    for row in rows:
        issues: list[RowFieldIssue] = []
        preview: dict[str, str] = {}

        _validate_complaint_text(row, issues)
        has_auto_normalization = _validate_event_occurred_at(row, issues, preview)

        for field_name in MAPPED_FIELDS:
            raw_value = getattr(row, field_name)
            if raw_value is None or not raw_value.strip():
                continue
            result = classifications_by_field[field_name][raw_value]
            if result.classification == ValueClassification.NEEDS_MAPPING:
                confidence = result.confidence.value  # "medium" / "low"
                issues.append(
                    RowFieldIssue(
                        row_number=row.row_number,
                        field=field_name,
                        provided_value=raw_value,
                        problem="needs_mapping",
                        confidence=confidence,
                        suggested_target_value=result.suggested_target_value,
                        suggested_action="accept_suggestion" if confidence == "medium" else "review_mapping",
                    )
                )
                if result.mapping_id is not None:
                    cluster_mapping_ids.add(result.mapping_id)
                    field_ex, norm_ex, raws = cluster_examples.get(result.mapping_id, (field_name, result.normalized_value, set()))
                    raws.add(raw_value)
                    cluster_examples[result.mapping_id] = (field_ex, norm_ex, raws)
            else:
                preview[field_name] = result.target_value
                if result.classification == ValueClassification.AUTO_NORMALIZED:
                    has_auto_normalization = True

        status = _row_status(issues, has_auto_normalization)
        summary[status] += 1
        results.append(
            RowAnalysisResult(
                row_number=row.row_number,
                status=status,
                issues=issues,
                normalized_preview=preview,
                source_file_name=row.source_file_name,
            )
        )

    pending_clusters: list[PendingClusterSummary] = []
    for mapping_id in cluster_mapping_ids:
        mapping = await mapping_service.mapping_repo.get_by_id(mapping_id)
        if mapping is None:
            continue
        _field_ex, _norm_ex, raws = cluster_examples[mapping_id]
        pending_clusters.append(
            PendingClusterSummary(
                field_name=mapping.field_name,
                raw_value_normalized=mapping.raw_value_normalized,
                example_values=sorted(raws),
                occurrence_count=mapping.occurrence_count,
                confidence=mapping.confidence.value,
                suggested_target_value=mapping.suggested_target_value,
                mapping_id=mapping.id,
                valid_choices=enum_choices_for_field(mapping.field_name),
            )
        )
    pending_clusters.sort(key=lambda c: c.occurrence_count, reverse=True)

    return results, summary, pending_clusters


def _validate_complaint_text(row: AnalyzeRowInput, issues: list[RowFieldIssue]) -> None:
    text = row.complaint_text
    if text is None or not text.strip():
        issues.append(
            RowFieldIssue(
                row_number=row.row_number,
                field="complaint_text",
                provided_value=text or "",
                problem="required_missing",
                suggested_action="provide_value",
            )
        )
    elif len(text.strip()) < _MIN_COMPLAINT_TEXT_LENGTH:
        issues.append(
            RowFieldIssue(
                row_number=row.row_number,
                field="complaint_text",
                provided_value=text,
                problem="invalid_format",
                suggested_action="fix_value",
            )
        )


def _validate_event_occurred_at(row: AnalyzeRowInput, issues: list[RowFieldIssue], preview: dict[str, str]) -> bool:
    """Returns True if the value required normalization (whitespace trimming) to be accepted."""
    if row.event_occurred_at is None or not row.event_occurred_at.strip():
        return False
    stripped = row.event_occurred_at.strip()
    try:
        datetime.fromisoformat(stripped)
        preview["event_occurred_at"] = stripped
        return stripped != row.event_occurred_at
    except ValueError:
        issues.append(
            RowFieldIssue(
                row_number=row.row_number,
                field="event_occurred_at",
                provided_value=row.event_occurred_at,
                problem="invalid_format",
                suggested_action="fix_value",
            )
        )
        return False


def _row_status(issues: list[RowFieldIssue], has_auto_normalization: bool) -> str:
    if not issues:
        return "auto_normalized" if has_auto_normalization else "accepted"
    statuses = set()
    for issue in issues:
        if issue.problem == "needs_mapping":
            statuses.add("needs_review" if issue.confidence == "low" else "suggested_mapping")
        else:
            statuses.add("rejected")
    return min(statuses, key=lambda s: _STATUS_PRIORITY[s])
