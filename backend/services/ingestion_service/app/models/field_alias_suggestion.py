from typing import Optional

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database.base import Base, PrimaryKeyMixin, TimestampMixin


class FieldAliasSuggestion(Base, PrimaryKeyMixin, TimestampMixin):
    """
    The controlled, curated synonym registry that powers MEDIUM-confidence
    classification (see mapping_service.classify_unique_values).

    Ownership:
    Owned by the Ingestion Service.

    Never written by the classifier and never inferred by fuzzy/semantic
    matching at runtime -- only through /field-mappings/alias-suggestions
    (POST/PUT), which validates `suggested_target_value` the same way
    mapping approval does (operational_area must be a real OperationalArea
    member; customer_region accepts free text). This table can never
    trigger a Postgres `ALTER TYPE` -- it stores plain validated strings.
    """

    __tablename__ = "field_alias_suggestions"

    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_value_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    suggested_target_value: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500))
    created_by: Mapped[Optional[str]] = mapped_column(String(255))

    __table_args__ = (
        UniqueConstraint(
            "field_name", "source_value_normalized", name="uq_field_alias_suggestions_field_source"
        ),
    )
