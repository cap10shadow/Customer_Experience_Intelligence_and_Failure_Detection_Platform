from typing import Sequence

"""
The role hierarchy defined by the frozen architecture (§11: "operator --
viewer + ...", "admin -- operator + ..."). Each role listed here is a
strict superset of every role before it -- a principal holding a higher
role automatically satisfies a lower role's requirement, matching the
matrix's own cumulative phrasing rather than requiring a user to hold
every intermediate role explicitly.

Do not add a role here that the frozen architecture doesn't name (no
superadmin/manager/analyst/etc. -- §11 is exhaustive).
"""

ROLE_HIERARCHY: tuple[str, ...] = ("viewer", "operator", "admin")

_ROLE_RANK = {role: rank for rank, role in enumerate(ROLE_HIERARCHY)}


def has_sufficient_role(user_roles: Sequence[str], minimum_role: str) -> bool:
    """
    True if any role the user holds meets or exceeds `minimum_role` in
    the hierarchy above. A user with no roles at all (the honest
    default for every account until an explicit role assignment exists
    -- role assignment itself is out of Batch 3's scope) never satisfies
    any check, including `viewer`.
    """
    minimum_rank = _ROLE_RANK[minimum_role]
    return any(_ROLE_RANK.get(role, -1) >= minimum_rank for role in user_roles)
