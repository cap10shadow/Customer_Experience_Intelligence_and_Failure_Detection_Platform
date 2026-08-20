import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from backend.services.ingestion_service.app.dependencies.repositories import (
    FieldAliasSuggestionRepo,
    FieldValueMappingRepo,
)
from backend.services.ingestion_service.app.models.field_alias_suggestion import FieldAliasSuggestion
from backend.services.ingestion_service.app.schemas.field_mapping import (
    AliasSuggestionCreateRequest,
    AliasSuggestionListResponse,
    AliasSuggestionResponse,
    AliasSuggestionUpdateRequest,
    ApproveMappingRequest,
    BulkApproveMappingRequest,
    BulkApproveMappingResponse,
    FieldValueMappingListResponse,
    FieldValueMappingResponse,
    RejectMappingRequest,
)
from backend.services.ingestion_service.app.services.mapping_service import (
    InvalidMappingTargetError,
    validate_target_for_field,
)
from backend.services.ingestion_service.app.services.normalization import normalize_value
from backend.shared.constants.enums.field_mapping import FieldValueMappingConfidence, FieldValueMappingType

router = APIRouter(prefix="/field-mappings", tags=["field-mappings"])


def _mapping_type_for(field_name: str, raw_example: str, target_value: str) -> FieldValueMappingType:
    if normalize_value(raw_example) == normalize_value(target_value):
        return FieldValueMappingType.CANONICAL_SELF
    return FieldValueMappingType.ALIAS


@router.get("/pending", response_model=FieldValueMappingListResponse, summary="List PENDING mappings for one field")
async def list_pending_mappings(
    repo: FieldValueMappingRepo,
    field_name: str = Query(...),
    confidence: Optional[FieldValueMappingConfidence] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=500),
):
    items = await repo.list_pending(field_name, confidence=confidence, skip=skip, limit=limit)
    total_count = await repo.count_pending(field_name, confidence=confidence)
    return FieldValueMappingListResponse(items=items, total_count=total_count, skip=skip, limit=limit)


@router.get("/approved", response_model=FieldValueMappingListResponse, summary="List APPROVED mappings for one field")
async def list_approved_mappings(
    repo: FieldValueMappingRepo,
    field_name: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=500),
):
    items = await repo.list_approved(field_name, skip=skip, limit=limit)
    total_count = await repo.count_approved(field_name)
    return FieldValueMappingListResponse(items=items, total_count=total_count, skip=skip, limit=limit)


@router.post(
    "/{mapping_id}/approve",
    response_model=FieldValueMappingResponse,
    summary="Approve one PENDING mapping -- the only endpoint (with bulk-approve) that may set status=APPROVED",
)
async def approve_mapping(mapping_id: uuid.UUID, payload: ApproveMappingRequest, repo: FieldValueMappingRepo):
    mapping = await repo.get_by_id(mapping_id)
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    try:
        validate_target_for_field(mapping.field_name, payload.target_value)
    except InvalidMappingTargetError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    mapping_type = _mapping_type_for(mapping.field_name, mapping.raw_value_original_example, payload.target_value)
    updated = await repo.set_approved(
        mapping_id, target_value=payload.target_value, mapping_type=mapping_type, reviewed_by=payload.reviewed_by
    )
    return updated


@router.post(
    "/bulk-approve",
    response_model=BulkApproveMappingResponse,
    summary="Approve many PENDING mappings to one target in a single decision",
)
async def bulk_approve_mappings(payload: BulkApproveMappingRequest, repo: FieldValueMappingRepo):
    approved: list = []
    for mapping_id in payload.mapping_ids:
        mapping = await repo.get_by_id(mapping_id)
        if mapping is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mapping {mapping_id} not found")
        try:
            validate_target_for_field(mapping.field_name, payload.target_value)
        except InvalidMappingTargetError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        mapping_type = _mapping_type_for(mapping.field_name, mapping.raw_value_original_example, payload.target_value)
        updated = await repo.set_approved(
            mapping_id, target_value=payload.target_value, mapping_type=mapping_type, reviewed_by=payload.reviewed_by
        )
        approved.append(updated)
    return BulkApproveMappingResponse(approved=approved)


@router.post(
    "/{mapping_id}/reject",
    response_model=FieldValueMappingResponse,
    summary="Reject one PENDING mapping",
)
async def reject_mapping(mapping_id: uuid.UUID, payload: RejectMappingRequest, repo: FieldValueMappingRepo):
    mapping = await repo.get_by_id(mapping_id)
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    updated = await repo.set_rejected(mapping_id, reviewed_by=payload.reviewed_by)
    return updated


@router.get(
    "/alias-suggestions",
    response_model=AliasSuggestionListResponse,
    summary="List curated alias-suggestion registry entries for one field",
)
async def list_alias_suggestions(
    repo: FieldAliasSuggestionRepo,
    field_name: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    items = await repo.list_by_field(field_name, skip=skip, limit=limit)
    return AliasSuggestionListResponse(items=items)


@router.post(
    "/alias-suggestions",
    response_model=AliasSuggestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Curate a new alias-suggestion registry entry (never invented by the classifier)",
)
async def create_alias_suggestion(payload: AliasSuggestionCreateRequest, repo: FieldAliasSuggestionRepo):
    try:
        validate_target_for_field(payload.field_name, payload.suggested_target_value)
    except InvalidMappingTargetError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    normalized_source = normalize_value(payload.source_value)
    existing = await repo.get_by_field_and_source(payload.field_name, normalized_source)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An alias suggestion for '{payload.source_value}' already exists on {payload.field_name}.",
        )

    suggestion = FieldAliasSuggestion(
        field_name=payload.field_name,
        source_value_normalized=normalized_source,
        suggested_target_value=payload.suggested_target_value,
        notes=payload.notes,
        created_by=payload.created_by,
    )
    created = await repo.create(suggestion)
    return created


@router.put(
    "/alias-suggestions/{suggestion_id}",
    response_model=AliasSuggestionResponse,
    summary="Update an existing alias-suggestion registry entry's target",
)
async def update_alias_suggestion(
    suggestion_id: uuid.UUID, payload: AliasSuggestionUpdateRequest, repo: FieldAliasSuggestionRepo
):
    suggestion = await repo.get_by_id(suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alias suggestion not found")
    try:
        validate_target_for_field(suggestion.field_name, payload.suggested_target_value)
    except InvalidMappingTargetError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    updated = await repo.update_target(suggestion_id, suggested_target_value=payload.suggested_target_value)
    return updated
