import hashlib


def generate_complaint_hash(external_reference: str | None, text: str) -> str:
    """
    Generates a deterministic payload hash for ingestion deduplication.
    Uses external reference if provided, otherwise hashes the text securely.
    """
    base_string = f"{external_reference or ''}::{text.strip().lower()}"
    return hashlib.sha256(base_string.encode("utf-8")).hexdigest()
