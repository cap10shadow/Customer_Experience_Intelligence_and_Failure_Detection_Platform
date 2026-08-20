from typing import Any, Dict, Optional

import httpx

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import get_json, post_resource, put_resource
from backend.services.gateway_service.app.core.errors import (
    ConflictError,
    DownstreamServiceError,
    GatewayValidationError,
    ResourceNotFoundError,
)
from backend.services.gateway_service.app.schemas.ingestion import (
    IngestionComplaintListResponse,
    IngestionComplaintRequest,
    IngestionComplaintResponse,
)

# ingestion_service mounts its complaints router at the application root
# (`app.include_router(complaints_router)` in ingestion_service/app/main.py),
# unlike every other downstream service -- there is no `/api/v1` segment
# to include here. This was the one real reason ingestion_service was
# unreachable through the Gateway at all before this module existed.
_COMPLAINTS_URL = f"{settings.INGESTION_SERVICE_URL}/complaints"
_COMPLAINTS_ANALYZE_URL = f"{_COMPLAINTS_URL}:analyze"
_COMPLAINTS_BATCH_URL = f"{_COMPLAINTS_URL}:batch"
_FIELD_MAPPINGS_URL = f"{settings.INGESTION_SERVICE_URL}/field-mappings"


async def create_complaint(
    client: httpx.AsyncClient, dataset_id: str, request: IngestionComplaintRequest
) -> IngestionComplaintResponse:
    """
    Forwards a real complaint payload to ingestion_service's own
    `POST /complaints?dataset_id=...` -- every complaint now belongs to a
    real Dataset (docs/DECISIONS.md AD-12); there is no dataset-less
    ingestion path anymore. No validation logic lives here beyond what
    `IngestionComplaintRequest` already enforces -- ingestion_service's
    own dedup-hash 409, missing-dataset 404, no-open-draft 409, and
    field-validation 422 are all propagated as real Gateway errors, never
    swallowed or turned into a fabricated success.
    """
    url = httpx.URL(_COMPLAINTS_URL).copy_merge_params({"dataset_id": dataset_id})
    response = await post_resource(client, str(url), json=request.model_dump(exclude_none=True))
    if response.status_code == 404:
        raise ResourceNotFoundError(f"Dataset {dataset_id} was not found.", details={"datasetId": dataset_id})
    if response.status_code == 409:
        raise ConflictError(
            _conflict_message(response),
            details={"externalReferenceId": request.external_reference_id, "datasetId": dataset_id},
        )
    if response.status_code == 422:
        raise GatewayValidationError(
            "The complaint payload was rejected by the ingestion service.",
            details=_safe_json(response),
        )
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return _to_response(response.json())


async def get_complaint(client: httpx.AsyncClient, complaint_id: str) -> IngestionComplaintResponse:
    complaint = await get_json(client, f"{_COMPLAINTS_URL}/{complaint_id}")
    if complaint is None:
        raise ResourceNotFoundError(f"Complaint {complaint_id} was not found.", details={"complaintId": complaint_id})
    return _to_response(complaint)


async def list_complaints(
    client: httpx.AsyncClient, *, dataset_id: str, skip: int, limit: int
) -> IngestionComplaintListResponse:
    payload = await get_json(client, _COMPLAINTS_URL, params={"dataset_id": dataset_id, "skip": skip, "limit": limit})
    payload = payload or {"items": [], "total_count": 0, "skip": skip, "limit": limit}
    return IngestionComplaintListResponse(
        items=[_to_response(item) for item in payload.get("items", [])],
        totalCount=payload.get("total_count", 0),
        skip=payload.get("skip", skip),
        limit=payload.get("limit", limit),
    )


def _conflict_message(response: httpx.Response) -> str:
    """
    Distinguishes ingestion_service's two real 409 causes (a dedup-hash
    collision vs. no open draft version to ingest into) using its own
    real error detail, rather than collapsing both into one generic
    sentence.
    """
    detail = _safe_json(response)
    if isinstance(detail, dict) and isinstance(detail.get("detail"), str):
        return detail["detail"]
    return "This request could not be completed because of a real conflict with the dataset's current state."


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


async def analyze_complaints(
    client: httpx.AsyncClient, dataset_id: str, request: Dict[str, Any], *, page: int, page_size: int
) -> Dict[str, Any]:
    """
    Forwards a client-parsed row batch to ingestion_service's
    `POST /complaints:analyze?dataset_id=...&page=...&page_size=...` --
    pure pass-through, no normalization/mapping/validation logic here.
    The response body is returned as-received (snake_case, matching
    ingestion_service's own contract) rather than remapped field-by-field
    into a parallel camelCase schema tree: this endpoint's payload is a
    deep, frequently-changing result structure (per-row issues, pending
    clusters), and hand-mirroring every nested field here would be
    exactly the kind of Gateway-side business/shape logic this proxy is
    meant to avoid -- ingestion_service's response is already the single
    source of truth for this contract.
    """
    url = httpx.URL(_COMPLAINTS_ANALYZE_URL).copy_merge_params(
        {"dataset_id": dataset_id, "page": str(page), "page_size": str(page_size)}
    )
    response = await post_resource(client, str(url), json=request)
    if response.status_code == 404:
        raise ResourceNotFoundError(f"Dataset {dataset_id} was not found.", details={"datasetId": dataset_id})
    if response.status_code == 422:
        raise GatewayValidationError("The analyze request was rejected by the ingestion service.", details=_safe_json(response))
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return response.json()


async def batch_submit_complaints(client: httpx.AsyncClient, dataset_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Forwards to `POST /complaints:batch?dataset_id=...` -- same pass-through rationale as `analyze_complaints`."""
    url = httpx.URL(_COMPLAINTS_BATCH_URL).copy_merge_params({"dataset_id": dataset_id})
    response = await post_resource(client, str(url), json=request)
    if response.status_code == 404:
        raise ResourceNotFoundError(f"Dataset {dataset_id} was not found.", details={"datasetId": dataset_id})
    if response.status_code == 409:
        raise ConflictError(_conflict_message(response), details={"datasetId": dataset_id})
    if response.status_code == 422:
        raise GatewayValidationError("The batch request was rejected by the ingestion service.", details=_safe_json(response))
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return response.json()


async def list_pending_field_mappings(
    client: httpx.AsyncClient, *, field_name: str, confidence: Optional[str], skip: int, limit: int
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"field_name": field_name, "skip": skip, "limit": limit}
    if confidence is not None:
        params["confidence"] = confidence
    payload = await get_json(client, f"{_FIELD_MAPPINGS_URL}/pending", params=params)
    return payload or {"items": [], "total_count": 0, "skip": skip, "limit": limit}


async def list_approved_field_mappings(client: httpx.AsyncClient, *, field_name: str, skip: int, limit: int) -> Dict[str, Any]:
    payload = await get_json(
        client, f"{_FIELD_MAPPINGS_URL}/approved", params={"field_name": field_name, "skip": skip, "limit": limit}
    )
    return payload or {"items": [], "total_count": 0, "skip": skip, "limit": limit}


async def approve_field_mapping(client: httpx.AsyncClient, mapping_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    response = await post_resource(client, f"{_FIELD_MAPPINGS_URL}/{mapping_id}/approve", json=request)
    if response.status_code == 404:
        raise ResourceNotFoundError(f"Mapping {mapping_id} was not found.", details={"mappingId": mapping_id})
    if response.status_code == 422:
        raise GatewayValidationError("The approval target was rejected by the ingestion service.", details=_safe_json(response))
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return response.json()


async def bulk_approve_field_mappings(client: httpx.AsyncClient, request: Dict[str, Any]) -> Dict[str, Any]:
    response = await post_resource(client, f"{_FIELD_MAPPINGS_URL}/bulk-approve", json=request)
    if response.status_code == 404:
        raise ResourceNotFoundError("One of the requested mappings was not found.", details=_safe_json(response))
    if response.status_code == 422:
        raise GatewayValidationError("The approval target was rejected by the ingestion service.", details=_safe_json(response))
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return response.json()


async def reject_field_mapping(client: httpx.AsyncClient, mapping_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    response = await post_resource(client, f"{_FIELD_MAPPINGS_URL}/{mapping_id}/reject", json=request)
    if response.status_code == 404:
        raise ResourceNotFoundError(f"Mapping {mapping_id} was not found.", details={"mappingId": mapping_id})
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return response.json()


async def list_alias_suggestions(client: httpx.AsyncClient, *, field_name: str) -> Dict[str, Any]:
    payload = await get_json(client, f"{_FIELD_MAPPINGS_URL}/alias-suggestions", params={"field_name": field_name})
    return payload or {"items": []}


async def create_alias_suggestion(client: httpx.AsyncClient, request: Dict[str, Any]) -> Dict[str, Any]:
    response = await post_resource(client, f"{_FIELD_MAPPINGS_URL}/alias-suggestions", json=request)
    if response.status_code == 422:
        raise GatewayValidationError("The alias target was rejected by the ingestion service.", details=_safe_json(response))
    if response.status_code == 409:
        raise ConflictError(_conflict_message(response), details=_safe_json(response))
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return response.json()


async def update_alias_suggestion(client: httpx.AsyncClient, suggestion_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    response = await put_resource(client, f"{_FIELD_MAPPINGS_URL}/alias-suggestions/{suggestion_id}", json=request)
    if response.status_code == 404:
        raise ResourceNotFoundError(f"Alias suggestion {suggestion_id} was not found.", details={"suggestionId": suggestion_id})
    if response.status_code == 422:
        raise GatewayValidationError("The alias target was rejected by the ingestion service.", details=_safe_json(response))
    if response.status_code >= 400:
        raise DownstreamServiceError(f"Ingestion service returned status {response.status_code}.")
    return response.json()


def _to_response(complaint: Dict[str, Any]) -> IngestionComplaintResponse:
    return IngestionComplaintResponse(
        id=str(complaint["id"]),
        datasetId=str(complaint["dataset_id"]),
        complaintText=complaint["complaint_text"],
        complaintTitle=complaint.get("complaint_title"),
        externalReferenceId=complaint.get("external_reference_id"),
        complaintSource=complaint.get("complaint_source"),
        sourceChannel=complaint.get("source_channel"),
        customerRegion=complaint.get("customer_region"),
        productCategory=complaint.get("product_category"),
        operationalArea=complaint.get("operational_area"),
        complaintStatus=str(complaint["complaint_status"]),
        processingStage=str(complaint["processing_stage"]),
        insertedAt=str(complaint["inserted_at"]),
    )
