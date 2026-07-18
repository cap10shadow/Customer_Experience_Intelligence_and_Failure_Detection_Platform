import uuid
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.nlp_service.app.models.complaint_enrichment import ComplaintEnrichment
from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel


class EnrichmentRepository:
    """
    Enrichment Repository

    Ownership:
    Owned by the NLP Service context.

    Operational Purpose:
    Responsible strictly for database persistence and retrieval of
    ComplaintEnrichment entities. Contains no NLP logic, no orchestration,
    and no HTTP communication — only data access.

    Architectural Boundaries:
    - Persistence and retrieval only.
    - Enrichment pipeline logic belongs in the service layer.
    - API validation belongs in routers and Pydantic schemas.
    - Cross-service communication belongs in HTTP client modules.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create_enrichment(
        self, enrichment: ComplaintEnrichment
    ) -> ComplaintEnrichment:
        """Persists a new enrichment record and flushes to the session."""
        self.session.add(enrichment)
        await self.session.flush()
        return enrichment

    # ------------------------------------------------------------------
    # Single-record reads
    # ------------------------------------------------------------------

    async def get_by_id(
        self, enrichment_id: uuid.UUID
    ) -> ComplaintEnrichment | None:
        """Retrieves an enrichment by its own primary key."""
        stmt = select(ComplaintEnrichment).where(
            ComplaintEnrichment.id == enrichment_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_complaint_id(
        self, complaint_id: uuid.UUID
    ) -> ComplaintEnrichment | None:
        """
        Retrieves the enrichment linked to a given complaint.

        Returns None if the complaint has not been enriched yet. Because the
        complaint_id column carries a unique constraint, at most one record can
        exist per complaint.
        """
        stmt = select(ComplaintEnrichment).where(
            ComplaintEnrichment.complaint_id == complaint_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Existence / idempotency checks
    # ------------------------------------------------------------------

    async def exists_for_complaint(self, complaint_id: uuid.UUID) -> bool:
        """
        Returns True if an enrichment already exists for the given complaint.

        Intended for idempotency guards at the pipeline entry point — callers
        should check this before invoking classifiers to avoid redundant work.
        """
        stmt = select(func.count(ComplaintEnrichment.id)).where(
            ComplaintEnrichment.complaint_id == complaint_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # ------------------------------------------------------------------
    # Collection reads
    # ------------------------------------------------------------------

    async def list_enrichments(
        self,
        skip: int = 0,
        limit: int = 100,
        sentiment_label: Optional[SentimentLabel] = None,
        urgency_label: Optional[UrgencyLabel] = None,
        issue_category: Optional[IssueCategory] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Sequence[ComplaintEnrichment]:
        """
        Returns enrichments matching the given filters, ordered by most recent
        enrichment_timestamp first. Supports offset-based pagination.
        """
        stmt = self._apply_filters(
            select(ComplaintEnrichment),
            sentiment_label=sentiment_label,
            urgency_label=urgency_label,
            issue_category=issue_category,
            start_date=start_date,
            end_date=end_date,
        )
        stmt = stmt.order_by(
            ComplaintEnrichment.enrichment_timestamp.desc(),
            ComplaintEnrichment.id.desc(),
        )
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_enrichments(
        self,
        sentiment_label: Optional[SentimentLabel] = None,
        urgency_label: Optional[UrgencyLabel] = None,
        issue_category: Optional[IssueCategory] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Returns the total count of enrichments matching the given filters."""
        stmt = self._apply_filters(
            select(func.count(ComplaintEnrichment.id)),
            sentiment_label=sentiment_label,
            urgency_label=urgency_label,
            issue_category=issue_category,
            start_date=start_date,
            end_date=end_date,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_by_sentiment(
        self,
        sentiment_label: SentimentLabel,
        limit: int = 100,
    ) -> Sequence[ComplaintEnrichment]:
        """Retrieves enrichments matching a specific sentiment, most recent first."""
        return await self.list_enrichments(
            sentiment_label=sentiment_label,
            limit=limit,
        )

    async def list_by_urgency(
        self,
        urgency_label: UrgencyLabel,
        limit: int = 100,
    ) -> Sequence[ComplaintEnrichment]:
        """Retrieves enrichments matching a specific urgency level, most recent first."""
        return await self.list_enrichments(
            urgency_label=urgency_label,
            limit=limit,
        )

    async def list_by_issue_category(
        self,
        issue_category: IssueCategory,
        limit: int = 100,
    ) -> Sequence[ComplaintEnrichment]:
        """Retrieves enrichments matching a specific issue category, most recent first."""
        return await self.list_enrichments(
            issue_category=issue_category,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_filters(
        self,
        stmt: Select,
        sentiment_label: Optional[SentimentLabel] = None,
        urgency_label: Optional[UrgencyLabel] = None,
        issue_category: Optional[IssueCategory] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Select:
        """
        Applies optional analytical filters to a SELECT statement.

        Centralised here so that list_enrichments and count_enrichments share
        identical filter logic — adding a new dimension requires one change.
        """
        if sentiment_label is not None:
            stmt = stmt.where(
                ComplaintEnrichment.sentiment_label == sentiment_label
            )
        if urgency_label is not None:
            stmt = stmt.where(
                ComplaintEnrichment.urgency_label == urgency_label
            )
        if issue_category is not None:
            stmt = stmt.where(
                ComplaintEnrichment.detected_issue_category == issue_category
            )
        if start_date is not None:
            stmt = stmt.where(
                ComplaintEnrichment.enrichment_timestamp >= start_date
            )
        if end_date is not None:
            stmt = stmt.where(
                ComplaintEnrichment.enrichment_timestamp <= end_date
            )
        return stmt
