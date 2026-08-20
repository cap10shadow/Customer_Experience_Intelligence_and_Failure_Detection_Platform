import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.ingestion_service.app.dependencies.repositories import (
    get_field_alias_suggestion_repository,
    get_field_value_mapping_repository,
)
from backend.services.ingestion_service.app.main import app
from backend.services.ingestion_service.tests._fakes import (
    FakeFieldAliasSuggestionRepository,
    FakeFieldValueMappingRepository,
)
from backend.shared.constants.enums.field_mapping import FieldValueMappingConfidence


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_repos():
    mapping_repo = FakeFieldValueMappingRepository()
    alias_repo = FakeFieldAliasSuggestionRepository()
    app.dependency_overrides[get_field_value_mapping_repository] = lambda: mapping_repo
    app.dependency_overrides[get_field_alias_suggestion_repository] = lambda: alias_repo
    yield mapping_repo, alias_repo
    app.dependency_overrides.pop(get_field_value_mapping_repository, None)
    app.dependency_overrides.pop(get_field_alias_suggestion_repository, None)


@pytest.mark.anyio
async def test_approve_mapping_sets_approved_and_target(mock_repos):
    mapping_repo, _ = mock_repos
    mapping = await mapping_repo.create(
        field_name="operational_area",
        raw_value_normalized="courier partner",
        raw_value_original_example="Courier Partner",
        confidence=FieldValueMappingConfidence.MEDIUM,
        suggested_target_value="logistics",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/field-mappings/{mapping.id}/approve", json={"target_value": "logistics", "reviewed_by": "ops@example.com"}
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["target_value"] == "logistics"


@pytest.mark.anyio
async def test_approve_mapping_rejects_invalid_operational_area_target(mock_repos):
    mapping_repo, _ = mock_repos
    mapping = await mapping_repo.create(
        field_name="operational_area",
        raw_value_normalized="courier partner",
        raw_value_original_example="Courier Partner",
        confidence=FieldValueMappingConfidence.MEDIUM,
        suggested_target_value=None,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            f"/field-mappings/{mapping.id}/approve", json={"target_value": "not_a_real_area"}
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_approve_mapping_accepts_customer_region_free_text(mock_repos):
    mapping_repo, _ = mock_repos
    mapping = await mapping_repo.create(
        field_name="customer_region",
        raw_value_normalized="mumbai",
        raw_value_original_example="Mumbai",
        confidence=FieldValueMappingConfidence.LOW,
        suggested_target_value=None,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(f"/field-mappings/{mapping.id}/approve", json={"target_value": "Mumbai"})
    assert response.status_code == 200
    assert response.json()["mapping_type"] == "canonical_self"


@pytest.mark.anyio
async def test_bulk_approve_resolves_many_mappings_to_one_target(mock_repos):
    mapping_repo, _ = mock_repos
    m1 = await mapping_repo.create(
        field_name="operational_area", raw_value_normalized="shipping", raw_value_original_example="Shipping",
        confidence=FieldValueMappingConfidence.MEDIUM, suggested_target_value="logistics",
    )
    m2 = await mapping_repo.create(
        field_name="operational_area", raw_value_normalized="courier", raw_value_original_example="Courier",
        confidence=FieldValueMappingConfidence.LOW, suggested_target_value=None,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/field-mappings/bulk-approve",
            json={"mapping_ids": [str(m1.id), str(m2.id)], "target_value": "logistics", "reviewed_by": "ops"},
        )
    assert response.status_code == 200
    approved = response.json()["approved"]
    assert len(approved) == 2
    assert all(a["target_value"] == "logistics" for a in approved)


@pytest.mark.anyio
async def test_reject_mapping_sets_rejected(mock_repos):
    mapping_repo, _ = mock_repos
    mapping = await mapping_repo.create(
        field_name="operational_area", raw_value_normalized="unknown thing", raw_value_original_example="Unknown Thing",
        confidence=FieldValueMappingConfidence.LOW, suggested_target_value=None,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(f"/field-mappings/{mapping.id}/reject", json={"reviewed_by": "ops"})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


@pytest.mark.anyio
async def test_list_pending_filters_by_confidence(mock_repos):
    mapping_repo, _ = mock_repos
    await mapping_repo.create(
        field_name="operational_area", raw_value_normalized="shipping", raw_value_original_example="Shipping",
        confidence=FieldValueMappingConfidence.MEDIUM, suggested_target_value="logistics",
    )
    await mapping_repo.create(
        field_name="operational_area", raw_value_normalized="abc operations", raw_value_original_example="ABC Operations",
        confidence=FieldValueMappingConfidence.LOW, suggested_target_value=None,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/field-mappings/pending?field_name=operational_area&confidence=medium")
    body = response.json()
    assert body["total_count"] == 1
    assert body["items"][0]["raw_value_normalized"] == "shipping"


# ------------------------------------------------------------------
# Correction 2: alias-registry target validation
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_alias_suggestion_rejects_invalid_operational_area_target(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/field-mappings/alias-suggestions",
            json={"field_name": "operational_area", "source_value": "Courier", "suggested_target_value": "not_a_real_area"},
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_alias_suggestion_accepts_valid_operational_area_target(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/field-mappings/alias-suggestions",
            json={"field_name": "operational_area", "source_value": "Courier", "suggested_target_value": "logistics"},
        )
    assert response.status_code == 201
    assert response.json()["source_value_normalized"] == "courier"


@pytest.mark.anyio
async def test_create_alias_suggestion_accepts_customer_region_free_text(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/field-mappings/alias-suggestions",
            json={"field_name": "customer_region", "source_value": "Home Delivery", "suggested_target_value": "delivery"},
        )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_create_alias_suggestion_rejects_duplicate_source(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        first = await client.post(
            "/field-mappings/alias-suggestions",
            json={"field_name": "operational_area", "source_value": "Courier", "suggested_target_value": "logistics"},
        )
        assert first.status_code == 201
        second = await client.post(
            "/field-mappings/alias-suggestions",
            json={"field_name": "operational_area", "source_value": "  Courier  ", "suggested_target_value": "logistics"},
        )
    assert second.status_code == 409


@pytest.mark.anyio
async def test_update_alias_suggestion_rejects_invalid_target(mock_repos):
    _, alias_repo = mock_repos
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/field-mappings/alias-suggestions",
            json={"field_name": "operational_area", "source_value": "Courier", "suggested_target_value": "logistics"},
        )
        suggestion_id = created.json()["id"]
        response = await client.put(
            f"/field-mappings/alias-suggestions/{suggestion_id}", json={"suggested_target_value": "not_a_real_area"}
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_alias_suggestions(mock_repos):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        await client.post(
            "/field-mappings/alias-suggestions",
            json={"field_name": "operational_area", "source_value": "Courier", "suggested_target_value": "logistics"},
        )
        response = await client.get("/field-mappings/alias-suggestions?field_name=operational_area")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
