import re

_SEPARATOR_RUN = re.compile(r"[\s_-]+")


def normalize_value(raw: str) -> str:
    """
    The single, deterministic definition of "same value" used everywhere
    in the ingestion mapping layer -- lookup, clustering, and dedup all
    call this and only this. Trim, collapse any run of whitespace,
    hyphens, or underscores into a single space, casefold. Hyphens and
    underscores are purely formatting choices for the SAME value (this
    matches the platform's pre-existing enum-normalization convention,
    e.g. "Existing Customer"/"existing-customer" both meaning
    `existing_customer`) -- collapsing them is still deterministic
    formatting normalization, not a semantic guess. This is what lets a
    real-world spelling like "Customer Support" match the canonical enum
    member `customer_support` as HIGH confidence instead of incorrectly
    falling through to the mapping workflow. No stemming, no synonym
    lookup, no semantic guessing beyond this: anything past
    whitespace/casing/separator formatting is a MEDIUM (registry) or LOW
    (human) decision, never made here.
    """
    return _SEPARATOR_RUN.sub(" ", raw.strip()).strip().casefold()
