from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Body, Depends, Query

from backend.services.gateway_service.app.core.authorization import require_role
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.ingestion import IngestionComplaintResponse
from backend.services.gateway_service.app.services.ingestion_proxy import (
    approve_field_mapping,
    bulk_approve_field_mappings,
    create_alias_suggestion,
    get_complaint,
    list_alias_suggestions,
    list_approved_field_mappings,
    list_pending_field_mappings,
    reject_field_mapping,
    update_alias_suggestion,
)

router = APIRouter(tags=["ingestion"])


@router.get("/ingestion/complaints/{complaint_id}", response_model=IngestionComplaintResponse)
async def get_ingestion_complaint(
    complaint_id: str,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> IngestionComplaintResponse:
    """
    Direct by-id lookup, kept dataset-independent since a complaint id is
    already globally unique -- unlike creation and listing (moved to
    `POST/GET /datasets/{datasetId}/complaints`, docs/DECISIONS.md AD-12),
    which are meaningless without a dataset to scope them to.
    """
    return await get_complaint(client, complaint_id)


# ------------------------------------------------------------------
# Field-value mapping review -- pure pass-through to ingestion_service's
# /field-mappings/* endpoints (mapping-persistence layer, not
# dataset-scoped -- reused across every dataset for a given field).
# See ingestion_proxy.py's mapping functions for why response bodies are
# forwarded as-received rather than remapped into a parallel schema.
# ------------------------------------------------------------------


@router.get("/field-mappings/pending", response_model=Dict[str, Any])
async def get_pending_field_mappings(
    field_name: str = Query(...),
    confidence: Optional[str] = Query(None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=500),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> Dict[str, Any]:
    return await list_pending_field_mappings(client, field_name=field_name, confidence=confidence, skip=skip, limit=limit)


@router.get("/field-mappings/approved", response_model=Dict[str, Any])
async def get_approved_field_mappings(
    field_name: str = Query(...),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=500),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> Dict[str, Any]:
    return await list_approved_field_mappings(client, field_name=field_name, skip=skip, limit=limit)


@router.post(
    "/field-mappings/{mapping_id}/approve", response_model=Dict[str, Any], dependencies=[Depends(require_role("operator"))]
)
async def post_approve_field_mapping(
    mapping_id: str, request: Dict[str, Any] = Body(...), client: httpx.AsyncClient = Depends(get_http_client)
) -> Dict[str, Any]:
    return await approve_field_mapping(client, mapping_id, request)


@router.post("/field-mappings/bulk-approve", response_model=Dict[str, Any], dependencies=[Depends(require_role("operator"))])
async def post_bulk_approve_field_mappings(
    request: Dict[str, Any] = Body(...), client: httpx.AsyncClient = Depends(get_http_client)
) -> Dict[str, Any]:
    return await bulk_approve_field_mappings(client, request)


@router.post(
    "/field-mappings/{mapping_id}/reject", response_model=Dict[str, Any], dependencies=[Depends(require_role("operator"))]
)
async def post_reject_field_mapping(
    mapping_id: str, request: Dict[str, Any] = Body(...), client: httpx.AsyncClient = Depends(get_http_client)
) -> Dict[str, Any]:
    return await reject_field_mapping(client, mapping_id, request)


@router.get("/field-mappings/alias-suggestions", response_model=Dict[str, Any])
async def get_alias_suggestions(
    field_name: str = Query(...), client: httpx.AsyncClient = Depends(get_http_client)
) -> Dict[str, Any]:
    return await list_alias_suggestions(client, field_name=field_name)


@router.post(
    "/field-mappings/alias-suggestions",
    response_model=Dict[str, Any],
    status_code=201,
    dependencies=[Depends(require_role("operator"))],
)
async def post_alias_suggestion(
    request: Dict[str, Any] = Body(...), client: httpx.AsyncClient = Depends(get_http_client)
) -> Dict[str, Any]:
    return await create_alias_suggestion(client, request)


@router.put(
    "/field-mappings/alias-suggestions/{suggestion_id}",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_role("operator"))],
)
async def put_alias_suggestion(
    suggestion_id: str, request: Dict[str, Any] = Body(...), client: httpx.AsyncClient = Depends(get_http_client)
) -> Dict[str, Any]:
    return await update_alias_suggestion(client, suggestion_id, request)
