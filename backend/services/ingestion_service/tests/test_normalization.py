from backend.services.ingestion_service.app.services.normalization import normalize_value


def test_normalize_value_trims_whitespace():
    assert normalize_value("  Courier Partner  ") == "courier partner"


def test_normalize_value_collapses_internal_whitespace():
    assert normalize_value("Courier   Partner") == "courier partner"


def test_normalize_value_casefolds():
    assert normalize_value("COURIER PARTNER") == "courier partner"
    assert normalize_value("Courier Partner") == "courier partner"
    assert normalize_value("courier partner") == "courier partner"


def test_normalize_value_deterministic():
    assert normalize_value("Home Delivery") == normalize_value("Home Delivery")


def test_normalize_value_idempotent():
    once = normalize_value("  Home   Delivery ")
    twice = normalize_value(once)
    assert once == twice


def test_normalize_value_whitespace_and_casing_variants_collapse_to_same_key():
    variants = ["Courier", "courier ", " Courier", "COURIER", "  courier  "]
    normalized = {normalize_value(v) for v in variants}
    assert normalized == {"courier"}


def test_normalize_value_collapses_hyphens_and_underscores_as_formatting_only():
    """
    Hyphens/underscores are pure formatting for the same value (matches
    the platform's pre-existing enum-normalization convention) -- this is
    what lets "Customer Support" match the canonical enum member
    `customer_support` as HIGH confidence instead of falling through to
    the mapping workflow.
    """
    variants = ["customer_support", "customer support", "Customer-Support", "CUSTOMER_SUPPORT", "customer  support"]
    normalized = {normalize_value(v) for v in variants}
    assert normalized == {"customer support"}
