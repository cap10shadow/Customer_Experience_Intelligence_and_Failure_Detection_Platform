from dataclasses import dataclass

from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel


@dataclass(frozen=True)
class NLPIntelligence:
    """
    Plain, persistence-independent view of a Phase 4 NLP enrichment result,
    as seen by the Recommendation Engine.

    Deliberately NOT the NLP Service's own `ComplaintEnrichment` ORM entity:
    this engine must never import across a service boundary (DATA-002).
    `SentimentLabel`, `UrgencyLabel`, and `IssueCategory` are genuinely
    shared enums (`backend.shared.constants.enums.complaint`), the same
    precedent Root Cause Service's own `Incident` already relies on. A later
    step is responsible for constructing this from a real enrichment record.

    Optional on `IntelligenceContext`: not every Incident necessarily has a
    representative enrichment snapshot attached at recommendation time.
    """

    sentiment_label: SentimentLabel
    urgency_label: UrgencyLabel
    issue_category: IssueCategory
    confidence_score: float
