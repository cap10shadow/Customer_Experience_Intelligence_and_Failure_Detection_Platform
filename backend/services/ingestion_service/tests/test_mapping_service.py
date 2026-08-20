import uuid

import pytest

from backend.services.ingestion_service.app.models.field_alias_suggestion import FieldAliasSuggestion
from backend.services.ingestion_service.app.services.mapping_service import (
    InvalidMappingTargetError,
    MappingService,
    ValueClassification,
    validate_target_for_field,
)
from backend.services.ingestion_service.tests._fakes import (
    FakeFieldAliasSuggestionRepository,
    FakeFieldValueMappingRepository,
)
from backend.shared.constants.enums.field_mapping import FieldValueMappingConfidence, FieldValueMappingStatus, FieldValueMappingType


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def repos():
    return FakeFieldValueMappingRepository(), FakeFieldAliasSuggestionRepository()


@pytest.fixture
def service(repos):
    mapping_repo, alias_repo = repos
    return MappingService(mapping_repo, alias_repo)


# ----------------------------------------------------------------------
# HIGH confidence
# ----------------------------------------------------------------------


@pytest.mark.anyio
async def test_enum_exact_match_classifies_valid_high(service):
    results = await service.classify_unique_values(
        "operational_area", {"logistics": 5}, analysis_session_id=uuid.uuid4()
    )
    result = results["logistics"]
    assert result.classification == ValueClassification.VALID
    assert result.confidence == FieldValueMappingConfidence.HIGH
    assert result.target_value == "logistics"


@pytest.mark.anyio
async def test_enum_casing_whitespace_variant_classifies_auto_normalized_high(service):
    results = await service.classify_unique_values(
        "operational_area", {" LOGISTICS ": 3}, analysis_session_id=uuid.uuid4()
    )
    result = results[" LOGISTICS "]
    assert result.classification == ValueClassification.AUTO_NORMALIZED
    assert result.confidence == FieldValueMappingConfidence.HIGH
    assert result.target_value == "logistics"


@pytest.mark.anyio
async def test_approved_mapping_match_classifies_high_and_reused(repos):
    mapping_repo, alias_repo = repos
    service = MappingService(mapping_repo, alias_repo)
    created = await mapping_repo.create(
        field_name="customer_region",
        raw_value_normalized="home delivery",
        raw_value_original_example="Home Delivery",
        confidence=FieldValueMappingConfidence.MEDIUM,
        suggested_target_value="delivery",
    )
    await mapping_repo.set_approved(
        created.id, target_value="delivery", mapping_type=FieldValueMappingType.ALIAS, reviewed_by="ops@example.com"
    )

    results = await service.classify_unique_values(
        "customer_region", {"Home Delivery": 12}, analysis_session_id=uuid.uuid4()
    )
    result = results["Home Delivery"]
    assert result.classification == ValueClassification.AUTO_NORMALIZED
    assert result.confidence == FieldValueMappingConfidence.HIGH
    assert result.target_value == "delivery"


# ----------------------------------------------------------------------
# MEDIUM confidence -- registry match, suggest-only
# ----------------------------------------------------------------------


@pytest.mark.anyio
async def test_registry_match_classifies_medium_suggest_only(repos):
    mapping_repo, alias_repo = repos
    service = MappingService(mapping_repo, alias_repo)
    await alias_repo.create(
        FieldAliasSuggestion(
            field_name="operational_area", source_value_normalized="courier partner", suggested_target_value="logistics"
        )
    )

    results = await service.classify_unique_values(
        "operational_area", {"Courier Partner": 42}, analysis_session_id=uuid.uuid4()
    )
    result = results["Courier Partner"]
    assert result.classification == ValueClassification.NEEDS_MAPPING
    assert result.confidence == FieldValueMappingConfidence.MEDIUM
    assert result.suggested_target_value == "logistics"
    assert result.target_value is None  # never auto-applied

    mapping = await mapping_repo.get_by_id(result.mapping_id)
    assert mapping.status == FieldValueMappingStatus.PENDING
    assert mapping.target_value is None


# ----------------------------------------------------------------------
# LOW confidence -- no match, no suggestion
# ----------------------------------------------------------------------


@pytest.mark.anyio
async def test_no_match_classifies_low_no_suggestion(service):
    results = await service.classify_unique_values(
        "operational_area", {"ABC Operations": 7}, analysis_session_id=uuid.uuid4()
    )
    result = results["ABC Operations"]
    assert result.classification == ValueClassification.NEEDS_MAPPING
    assert result.confidence == FieldValueMappingConfidence.LOW
    assert result.suggested_target_value is None
    assert result.target_value is None


@pytest.mark.anyio
async def test_clustering_groups_by_exact_normalized_value_only(service):
    """'Courier'/'courier '/' Courier' collapse into one PENDING row; 'Shipping' stays distinct (no fuzzy merging)."""
    results = await service.classify_unique_values(
        "operational_area",
        {"Courier": 10, "courier ": 5, " Courier": 3, "Shipping": 8},
        analysis_session_id=uuid.uuid4(),
    )
    assert results["Courier"].mapping_id == results["courier "].mapping_id == results[" Courier"].mapping_id
    assert results["Shipping"].mapping_id != results["Courier"].mapping_id


# ----------------------------------------------------------------------
# Correction 1 -- occurrence-count correctness
# ----------------------------------------------------------------------


@pytest.mark.anyio
async def test_reanalyzing_same_session_does_not_double_count(repos):
    mapping_repo, alias_repo = repos
    service = MappingService(mapping_repo, alias_repo)
    session_1 = uuid.uuid4()

    r1 = await service.classify_unique_values("operational_area", {"ABC Operations": 20}, analysis_session_id=session_1)
    mapping_id = r1["ABC Operations"].mapping_id
    assert (await mapping_repo.get_by_id(mapping_id)).occurrence_count == 20

    # Re-analyze the identical rows, SAME session -- must not inflate.
    await service.classify_unique_values("operational_area", {"ABC Operations": 20}, analysis_session_id=session_1)
    await service.classify_unique_values("operational_area", {"ABC Operations": 20}, analysis_session_id=session_1)
    assert (await mapping_repo.get_by_id(mapping_id)).occurrence_count == 20


@pytest.mark.anyio
async def test_new_session_increases_occurrence_count(repos):
    mapping_repo, alias_repo = repos
    service = MappingService(mapping_repo, alias_repo)
    session_1 = uuid.uuid4()
    session_2 = uuid.uuid4()

    r1 = await service.classify_unique_values("operational_area", {"ABC Operations": 20}, analysis_session_id=session_1)
    mapping_id = r1["ABC Operations"].mapping_id

    # A genuinely new upload/session with 5 more occurrences of the same value.
    await service.classify_unique_values("operational_area", {"ABC Operations": 5}, analysis_session_id=session_2)
    assert (await mapping_repo.get_by_id(mapping_id)).occurrence_count == 25


# ----------------------------------------------------------------------
# Correction 2 -- alias-registry target validation
# ----------------------------------------------------------------------


def test_validate_target_for_field_rejects_invalid_operational_area():
    with pytest.raises(InvalidMappingTargetError):
        validate_target_for_field("operational_area", "not_a_real_area")


def test_validate_target_for_field_accepts_valid_operational_area():
    validate_target_for_field("operational_area", "logistics")  # must not raise


def test_validate_target_for_field_accepts_customer_region_free_text():
    validate_target_for_field("customer_region", "Anything Reasonable")  # must not raise


def test_validate_target_for_field_rejects_empty_customer_region():
    with pytest.raises(InvalidMappingTargetError):
        validate_target_for_field("customer_region", "   ")


# ----------------------------------------------------------------------
# Correction 3 -- PENDING re-evaluation
# ----------------------------------------------------------------------


@pytest.mark.anyio
async def test_pending_low_upgrades_to_medium_when_registry_entry_added_later(repos):
    mapping_repo, alias_repo = repos
    service = MappingService(mapping_repo, alias_repo)
    session_1 = uuid.uuid4()

    r1 = await service.classify_unique_values("operational_area", {"ABC Operations": 7}, analysis_session_id=session_1)
    assert r1["ABC Operations"].confidence == FieldValueMappingConfidence.LOW
    mapping_id = r1["ABC Operations"].mapping_id

    # Registry updated after the fact.
    await alias_repo.create(
        FieldAliasSuggestion(
            field_name="operational_area", source_value_normalized="abc operations", suggested_target_value="customer_support"
        )
    )

    # Re-analyze the SAME rows, same session (idempotent occurrence, per correction 1).
    r2 = await service.classify_unique_values("operational_area", {"ABC Operations": 7}, analysis_session_id=session_1)
    result = r2["ABC Operations"]
    assert result.confidence == FieldValueMappingConfidence.MEDIUM
    assert result.suggested_target_value == "customer_support"

    mapping = await mapping_repo.get_by_id(mapping_id)
    assert mapping.status == FieldValueMappingStatus.PENDING  # never auto-approved
    assert mapping.target_value is None
    assert mapping.occurrence_count == 7  # unaffected by the re-analyze, same session


@pytest.mark.anyio
async def test_pending_medium_stays_medium_and_idempotent_when_registry_unchanged(repos):
    mapping_repo, alias_repo = repos
    service = MappingService(mapping_repo, alias_repo)
    await alias_repo.create(
        FieldAliasSuggestion(
            field_name="operational_area", source_value_normalized="courier partner", suggested_target_value="logistics"
        )
    )
    session_1 = uuid.uuid4()

    r1 = await service.classify_unique_values("operational_area", {"Courier Partner": 5}, analysis_session_id=session_1)
    r2 = await service.classify_unique_values("operational_area", {"Courier Partner": 5}, analysis_session_id=session_1)

    assert r1["Courier Partner"].confidence == r2["Courier Partner"].confidence == FieldValueMappingConfidence.MEDIUM
    assert r1["Courier Partner"].suggested_target_value == r2["Courier Partner"].suggested_target_value == "logistics"


# ----------------------------------------------------------------------
# Invariant: the classifier never approves anything, under any branch
# ----------------------------------------------------------------------


@pytest.mark.anyio
async def test_classifier_never_sets_approved_status_or_target_value(repos):
    """Property-style check across every classification branch this module can take."""
    mapping_repo, alias_repo = repos
    service = MappingService(mapping_repo, alias_repo)
    await alias_repo.create(
        FieldAliasSuggestion(
            field_name="operational_area", source_value_normalized="courier partner", suggested_target_value="logistics"
        )
    )
    session_1 = uuid.uuid4()

    # Exercise HIGH (enum match), MEDIUM (registry), and LOW (no match) branches.
    await service.classify_unique_values(
        "operational_area",
        {"Logistics": 1, "Courier Partner": 1, "ABC Operations": 1},
        analysis_session_id=session_1,
    )
    # Re-run to also exercise the PENDING re-evaluation branches.
    await service.classify_unique_values(
        "operational_area",
        {"Logistics": 1, "Courier Partner": 1, "ABC Operations": 1},
        analysis_session_id=uuid.uuid4(),
    )

    for row in mapping_repo.rows.values():
        assert row.status != FieldValueMappingStatus.APPROVED
        assert row.target_value is None
