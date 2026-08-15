"""
Pure unit tests for the role hierarchy (Phase 13 Batch 3, §11). No
database, no HTTP.
"""

from backend.services.gateway_service.app.core.roles import ROLE_HIERARCHY, has_sufficient_role


def test_hierarchy_is_exactly_viewer_operator_admin_in_that_order():
    assert ROLE_HIERARCHY == ("viewer", "operator", "admin")


def test_viewer_satisfies_viewer_requirement():
    assert has_sufficient_role(["viewer"], "viewer") is True


def test_viewer_does_not_satisfy_operator_requirement():
    assert has_sufficient_role(["viewer"], "operator") is False


def test_operator_satisfies_both_viewer_and_operator_requirements():
    assert has_sufficient_role(["operator"], "viewer") is True
    assert has_sufficient_role(["operator"], "operator") is True


def test_operator_does_not_satisfy_admin_requirement():
    assert has_sufficient_role(["operator"], "admin") is False


def test_admin_satisfies_every_requirement():
    assert has_sufficient_role(["admin"], "viewer") is True
    assert has_sufficient_role(["admin"], "operator") is True
    assert has_sufficient_role(["admin"], "admin") is True


def test_no_roles_at_all_never_satisfies_any_requirement_including_viewer():
    assert has_sufficient_role([], "viewer") is False


def test_an_unrecognized_role_name_never_satisfies_any_requirement():
    assert has_sufficient_role(["not-a-real-role"], "viewer") is False


def test_multiple_roles_use_the_highest_one():
    assert has_sufficient_role(["viewer", "admin"], "operator") is True
