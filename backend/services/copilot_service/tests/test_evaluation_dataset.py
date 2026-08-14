"""Tests for evaluation dataset loading/validation (Batch 6)."""

import json

import pytest

from backend.services.copilot_service.app.evaluation.dataset import DatasetValidationError, load_dataset


def test_real_dataset_file_loads_and_validates():
    dataset = load_dataset()
    assert dataset.dataset_kind == "synthetic_evaluation_fixtures"
    assert len(dataset.cases) > 0


def test_real_dataset_case_ids_are_unique():
    dataset = load_dataset()
    ids = [case.case_id for case in dataset.cases]
    assert len(ids) == len(set(ids))


def test_conversation_turn_2_references_an_earlier_case():
    """The conversation-continuity fixture must reference a case that runs before it, never itself or a later one."""
    dataset = load_dataset()
    case_ids_in_order = [case.case_id for case in dataset.cases]
    for index, case in enumerate(dataset.cases):
        if case.conversation_id_from_case is not None:
            referenced_index = case_ids_in_order.index(case.conversation_id_from_case)
            assert referenced_index < index


def test_missing_dataset_file_raises_a_clear_error(tmp_path):
    missing_path = tmp_path / "does_not_exist.json"

    with pytest.raises(DatasetValidationError, match="not found"):
        load_dataset(missing_path)


def test_malformed_json_raises_a_clear_error(tmp_path):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{ not valid json", encoding="utf-8")

    with pytest.raises(DatasetValidationError, match="not valid JSON"):
        load_dataset(bad_path)


def test_case_missing_required_field_raises_a_clear_validation_error(tmp_path):
    bad_path = tmp_path / "missing_field.json"
    bad_path.write_text(
        json.dumps({"dataset_kind": "synthetic_evaluation_fixtures", "cases": [{"case_id": "x"}]}), encoding="utf-8"
    )

    with pytest.raises(DatasetValidationError, match="failed validation"):
        load_dataset(bad_path)


def test_unknown_field_on_a_case_is_rejected_not_silently_ignored(tmp_path):
    bad_path = tmp_path / "extra_field.json"
    bad_path.write_text(
        json.dumps(
            {
                "dataset_kind": "synthetic_evaluation_fixtures",
                "cases": [
                    {
                        "case_id": "x",
                        "category": "c",
                        "description": "d",
                        "message": "m",
                        "unexpected_field": "should not be accepted",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DatasetValidationError, match="failed validation"):
        load_dataset(bad_path)


def test_wrong_dataset_kind_is_rejected(tmp_path):
    """`dataset_kind` must be exactly 'synthetic_evaluation_fixtures' -- guards against a real-production-data file being loaded here by mistake."""
    bad_path = tmp_path / "wrong_kind.json"
    bad_path.write_text(json.dumps({"dataset_kind": "production_data", "cases": []}), encoding="utf-8")

    with pytest.raises(DatasetValidationError, match="failed validation"):
        load_dataset(bad_path)
