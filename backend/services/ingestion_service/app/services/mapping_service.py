import uuid
from dataclasses import dataclass
from typing import Optional

from backend.services.ingestion_service.app.repositories.field_alias_suggestion_repository import (
    FieldAliasSuggestionRepository,
)
from backend.services.ingestion_service.app.repositories.field_value_mapping_repository import (
    FieldValueMappingRepository,
)
from backend.services.ingestion_service.app.services.normalization import normalize_value
from backend.shared.constants.enums.business_impact import OperationalArea, ServiceType
from backend.shared.constants.enums.complaint import CustomerSegment, CustomerType, SourceChannel
from backend.shared.constants.enums.field_mapping import FieldValueMappingConfidence, FieldValueMappingStatus

# Every categorical field that participates in this mapping layer.
# customer_region is free text (any non-empty normalized value is a
# valid target); the rest are backed by a fixed internal enum, so
# unfamiliar values become reviewable mapping clusters instead of a
# hard per-row rejection -- one shared abstraction for every
# canonical-vocabulary field instead of a per-field strict-validation
# path.
MAPPED_FIELDS = {
    "customer_region",
    "operational_area",
    "source_channel",
    "customer_segment",
    "customer_type",
    "service_type",
}

_ENUM_FIELDS = {
    "operational_area": OperationalArea,
    "source_channel": SourceChannel,
    "customer_segment": CustomerSegment,
    "customer_type": CustomerType,
    "service_type": ServiceType,
}


def enum_choices_for_field(field_name: str) -> Optional[list[str]]:
    """Valid canonical target choices for an enum-backed mapped field, or None for free-text fields."""
    enum_cls = _ENUM_FIELDS.get(field_name)
    return enum_cls.values() if enum_cls is not None else None


class ValueClassification:
    """Row-level classification outcomes this module produces (not a DB enum -- internal to the analyze response)."""

    VALID = "valid"
    AUTO_NORMALIZED = "auto_normalized"
    NEEDS_MAPPING = "needs_mapping"


@dataclass(frozen=True)
class ClassificationResult:
    raw_value: str
    normalized_value: str
    classification: str
    confidence: FieldValueMappingConfidence
    target_value: Optional[str] = None
    suggested_target_value: Optional[str] = None
    mapping_id: Optional[uuid.UUID] = None


class InvalidMappingTargetError(ValueError):
    """Raised when a target_value is not valid for the given field (e.g. not a real OperationalArea member)."""


def validate_target_for_field(field_name: str, target_value: str) -> None:
    """
    The single guard shared by mapping approval (POST /field-mappings/{id}/approve,
    /bulk-approve) and the alias-suggestion registry
    (POST/PUT /field-mappings/alias-suggestions) -- both enforcement points
    call this exact function so they can never drift apart.

    Enum-backed fields (operational_area, source_channel,
    customer_segment, customer_type, service_type): target_value must be
    a real member of that field's enum (by value, matching how it's
    represented in every schema/API payload throughout the codebase).
    This NEVER extends the Postgres enum -- membership is checked
    against the current Python enum only.
    customer_region: free text, any non-empty normalized value is
    accepted -- it's an evolving canonical vocabulary bounded to actual
    human approvals/curated registry entries, never invented by the
    classifier.
    """
    enum_cls = _ENUM_FIELDS.get(field_name)
    if enum_cls is not None:
        if not enum_cls.has_value(target_value):
            raise InvalidMappingTargetError(
                f"'{target_value}' is not a valid value for {field_name}. "
                f"Must be one of: {', '.join(enum_cls.values())}."
            )
        return

    if not target_value or not target_value.strip():
        raise InvalidMappingTargetError(f"target_value for {field_name} must not be empty.")


class MappingService:
    """
    The three-tier classifier: HIGH (deterministic, auto), MEDIUM
    (curated registry match, suggest-only), LOW (no match, ask the
    user). See classify_unique_values for the full decision order.
    """

    def __init__(
        self,
        mapping_repo: FieldValueMappingRepository,
        alias_repo: FieldAliasSuggestionRepository,
    ) -> None:
        self.mapping_repo = mapping_repo
        self.alias_repo = alias_repo

    async def classify_unique_values(
        self,
        field_name: str,
        unique_raw_values_with_counts: dict[str, int],
        analysis_session_id: uuid.UUID,
        first_seen_dataset_id: Optional[uuid.UUID] = None,
    ) -> dict[str, ClassificationResult]:
        """
        Classifies every distinct raw value for one field exactly once,
        regardless of how many rows share it -- two-to-three DB round
        trips total (mapping lookup, alias lookup, occurrence upserts),
        never O(rows).

        Returns a dict keyed by the ORIGINAL raw value (not normalized),
        since callers need to map classification back onto every row
        sharing that raw string. Multiple distinct raw strings that
        normalize to the same key (e.g. "Courier" / "courier ") are
        classified together as one cluster, but each keeps its own entry
        in the returned dict with its own VALID-vs-AUTO_NORMALIZED
        distinction (only an exact, unnormalized match to the target is
        VALID).
        """
        normalized_groups: dict[str, list[tuple[str, int]]] = {}
        for raw, count in unique_raw_values_with_counts.items():
            normalized_groups.setdefault(normalize_value(raw), []).append((raw, count))
        if not normalized_groups:
            return {}

        existing_mappings = await self.mapping_repo.bulk_get_by_field(field_name, normalized_groups.keys())
        alias_suggestions = await self.alias_repo.bulk_get_by_field(field_name, normalized_groups.keys())

        enum_cls = _ENUM_FIELDS.get(field_name)
        enum_lookup = None
        if enum_cls is not None:
            enum_lookup = {normalize_value(member.value): member for member in enum_cls}

        results: dict[str, ClassificationResult] = {}

        for normalized, raw_and_counts in normalized_groups.items():
            total_count = sum(count for _raw, count in raw_and_counts)
            existing = existing_mappings.get(normalized)
            mapping_row_id: Optional[uuid.UUID] = None

            if existing is not None and existing.status == FieldValueMappingStatus.APPROVED:
                # HIGH -- previously human-approved, now deterministic. Never re-evaluated.
                target = existing.target_value
                confidence = FieldValueMappingConfidence.HIGH
                suggested = existing.suggested_target_value
                mapping_row_id = existing.id

            elif enum_lookup is not None and normalized in enum_lookup:
                # HIGH -- deterministic exact/normalized enum match. No FieldValueMapping row involved.
                target = enum_lookup[normalized].value
                confidence = FieldValueMappingConfidence.HIGH
                suggested = None

            elif existing is not None and existing.status == FieldValueMappingStatus.PENDING:
                # Correction 3: re-evaluate against the CURRENT registry state, but only
                # ever upgrade LOW -> MEDIUM by attaching a suggestion. Never touch
                # status/target_value here -- that remains exclusively a human decision.
                if existing.confidence == FieldValueMappingConfidence.LOW and normalized in alias_suggestions:
                    new_suggestion = alias_suggestions[normalized]
                    await self.mapping_repo.update_confidence_and_suggestion(
                        existing.id,
                        confidence=FieldValueMappingConfidence.MEDIUM,
                        suggested_target_value=new_suggestion,
                    )
                    confidence = FieldValueMappingConfidence.MEDIUM
                    suggested = new_suggestion
                else:
                    # PENDING MEDIUM stays MEDIUM; PENDING LOW with still no match stays LOW.
                    confidence = existing.confidence
                    suggested = existing.suggested_target_value
                target = None
                mapping_row_id = existing.id

            elif normalized in alias_suggestions:
                # MEDIUM -- controlled registry match, suggest-only, NEVER auto-approved.
                suggested = alias_suggestions[normalized]
                created = await self.mapping_repo.create(
                    field_name=field_name,
                    raw_value_normalized=normalized,
                    raw_value_original_example=raw_and_counts[0][0],
                    confidence=FieldValueMappingConfidence.MEDIUM,
                    suggested_target_value=suggested,
                    first_seen_dataset_id=first_seen_dataset_id,
                )
                confidence = FieldValueMappingConfidence.MEDIUM
                target = None
                mapping_row_id = created.id

            else:
                # LOW -- no canonical or registry match. Propose nothing, ask the user.
                created = await self.mapping_repo.create(
                    field_name=field_name,
                    raw_value_normalized=normalized,
                    raw_value_original_example=raw_and_counts[0][0],
                    confidence=FieldValueMappingConfidence.LOW,
                    suggested_target_value=None,
                    first_seen_dataset_id=first_seen_dataset_id,
                )
                confidence = FieldValueMappingConfidence.LOW
                target = None
                suggested = None
                mapping_row_id = created.id

            classification_needs_mapping = target is None
            if mapping_row_id is not None:
                await self.mapping_repo.record_occurrence(mapping_row_id, analysis_session_id, row_count=total_count)

            for raw, count in raw_and_counts:
                if classification_needs_mapping:
                    classification = ValueClassification.NEEDS_MAPPING
                else:
                    classification = ValueClassification.VALID if raw == target else ValueClassification.AUTO_NORMALIZED
                results[raw] = ClassificationResult(
                    raw_value=raw,
                    normalized_value=normalized,
                    classification=classification,
                    confidence=confidence,
                    target_value=target,
                    suggested_target_value=suggested,
                    mapping_id=mapping_row_id,
                )

        return results
