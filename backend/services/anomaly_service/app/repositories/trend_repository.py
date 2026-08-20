import uuid
from datetime import date, datetime
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.anomaly_service.app.repositories.read_models import (
    complaint_enrichments_table,
    complaints_table,
)
from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel


class TrendRepository:
    """
    Trend Repository

    Ownership:
    Owned by the Anomaly Service context.

    Operational Purpose:
    Responsible strictly for read-only aggregation queries over complaint
    and complaint-enrichment data. Contains no trend interpretation, no
    scoring, and no response shaping — only data access.

    Architectural Boundaries:
    - Read-only. The Trend Engine never writes to these tables.
    - Aggregation and grouping happen here, in SQL, for efficiency on large
      datasets. Turning raw rows into API-shaped trend metrics belongs to
      the aggregator classes in app/services/aggregators/.

    Dataset scoping (docs/DECISIONS.md AD-12): every method requires
    `dataset_id` and filters `complaints_table.c.dataset_id == dataset_id`
    -- this is what makes anomaly/incident detection genuinely per-dataset
    rather than a global scan. The enrichment-based methods (category,
    urgency, sentiment) have no `dataset_id` column of their own
    (`complaint_enrichments` is a permanent per-complaint property, never
    reassigned to a dataset), so they join back to `complaints_table` to
    apply the same filter.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_complaints_by_day(
        self, start: datetime, end: datetime, dataset_id: uuid.UUID
    ) -> Sequence[tuple[date, int]]:
        """Returns (day, complaint_count) pairs for non-deleted complaints in range, scoped to one dataset."""
        day = func.date(complaints_table.c.event_occurred_at).label("day")
        stmt = (
            select(day, func.count(complaints_table.c.id))
            .where(
                complaints_table.c.dataset_id == dataset_id,
                complaints_table.c.is_deleted.is_(False),
                complaints_table.c.event_occurred_at >= start,
                complaints_table.c.event_occurred_at <= end,
            )
            .group_by(day)
            .order_by(day)
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def count_complaints_by_region(
        self, start: datetime, end: datetime, dataset_id: uuid.UUID
    ) -> Sequence[tuple[str, int]]:
        """Returns (region, complaint_count) pairs for non-deleted complaints in range, scoped to one dataset."""
        region = func.coalesce(complaints_table.c.customer_region, "unknown").label("region")
        stmt = (
            select(region, func.count(complaints_table.c.id))
            .where(
                complaints_table.c.dataset_id == dataset_id,
                complaints_table.c.is_deleted.is_(False),
                complaints_table.c.event_occurred_at >= start,
                complaints_table.c.event_occurred_at <= end,
            )
            .group_by(region)
            .order_by(func.count(complaints_table.c.id).desc())
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def count_enrichments_by_category(
        self, start: datetime, end: datetime, dataset_id: uuid.UUID
    ) -> Sequence[tuple[IssueCategory, int]]:
        """Returns (issue_category, count) pairs for enrichments in range, scoped to one dataset via a join back to complaints."""
        category = complaint_enrichments_table.c.detected_issue_category
        stmt = (
            select(category, func.count(complaint_enrichments_table.c.id))
            .select_from(
                complaint_enrichments_table.join(
                    complaints_table, complaint_enrichments_table.c.complaint_id == complaints_table.c.id
                )
            )
            .where(
                complaints_table.c.dataset_id == dataset_id,
                category.is_not(None),
                complaint_enrichments_table.c.enrichment_timestamp >= start,
                complaint_enrichments_table.c.enrichment_timestamp <= end,
            )
            .group_by(category)
            .order_by(func.count(complaint_enrichments_table.c.id).desc())
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def count_enrichments_by_urgency(
        self, start: datetime, end: datetime, dataset_id: uuid.UUID
    ) -> Sequence[tuple[UrgencyLabel, int]]:
        """Returns (urgency_label, count) pairs for enrichments in range, scoped to one dataset via a join back to complaints."""
        urgency = complaint_enrichments_table.c.urgency_label
        stmt = (
            select(urgency, func.count(complaint_enrichments_table.c.id))
            .select_from(
                complaint_enrichments_table.join(
                    complaints_table, complaint_enrichments_table.c.complaint_id == complaints_table.c.id
                )
            )
            .where(
                complaints_table.c.dataset_id == dataset_id,
                urgency.is_not(None),
                complaint_enrichments_table.c.enrichment_timestamp >= start,
                complaint_enrichments_table.c.enrichment_timestamp <= end,
            )
            .group_by(urgency)
            .order_by(func.count(complaint_enrichments_table.c.id).desc())
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def count_enrichments_by_day_and_sentiment(
        self, start: datetime, end: datetime, dataset_id: uuid.UUID
    ) -> Sequence[tuple[date, SentimentLabel, int]]:
        """
        Returns (day, sentiment_label, count) triples for enrichments in range,
        scoped to one dataset via a join back to complaints. Grouped by both
        day and label so the aggregator can derive a daily average sentiment
        score without pulling individual enrichment rows.
        """
        day = func.date(complaint_enrichments_table.c.enrichment_timestamp).label("day")
        sentiment = complaint_enrichments_table.c.sentiment_label
        stmt = (
            select(day, sentiment, func.count(complaint_enrichments_table.c.id))
            .select_from(
                complaint_enrichments_table.join(
                    complaints_table, complaint_enrichments_table.c.complaint_id == complaints_table.c.id
                )
            )
            .where(
                complaints_table.c.dataset_id == dataset_id,
                sentiment.is_not(None),
                complaint_enrichments_table.c.enrichment_timestamp >= start,
                complaint_enrichments_table.c.enrichment_timestamp <= end,
            )
            .group_by(day, sentiment)
            .order_by(day)
        )
        result = await self.session.execute(stmt)
        return result.all()
