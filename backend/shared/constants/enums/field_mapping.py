from backend.shared.constants.enums.base import BaseStringEnum


class FieldValueMappingConfidence(BaseStringEnum):
    """
    How a raw vocabulary value was classified against a field's canonical
    taxonomy.

    HIGH: deterministic exact/normalized match -- an already-approved
    mapping's target, or a real enum member (for enum-constrained
    fields). Safe to auto-canonicalize with no human step.
    MEDIUM: matched a curated field_alias_suggestions registry entry.
    Suggest-only -- never auto-applied, always requires explicit human
    approval (individual or bulk).
    LOW: no canonical or registry match. No target is proposed; the
    human must decide.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FieldValueMappingStatus(BaseStringEnum):
    """
    Lifecycle of one field_value_mappings row.

    PENDING: awaiting a human decision. The classifier is the only
    automated writer of PENDING rows (create, or confidence/suggestion
    refresh) -- it never transitions a row out of PENDING.
    APPROVED: a human explicitly approved a target_value via
    /field-mappings/{id}/approve or /bulk-approve. Deterministic and
    reused on every future classification.
    REJECTED: a human explicitly rejected this value -- rows using it at
    batch time are rejected with a stated reason, never guessed.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class FieldValueMappingType(BaseStringEnum):
    """
    ALIAS: the approved target_value differs from the raw value (e.g.
    "Courier" -> "Logistics").
    CANONICAL_SELF: the raw value was approved as its own canonical form
    verbatim (e.g. "Mumbai" -> "Mumbai", or a "Keep as Other" decision on
    customer_region) -- still persisted so it is remembered as VALID next
    time instead of being re-flagged as NEEDS_MAPPING.
    """

    ALIAS = "alias"
    CANONICAL_SELF = "canonical_self"
