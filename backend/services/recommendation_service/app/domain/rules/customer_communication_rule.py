from typing import List, Tuple

from backend.services.recommendation_service.app.domain import scoring
from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_rule import RecommendationRule
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence
from backend.shared.constants.enums.complaint import SentimentLabel

NEGATIVE_SENTIMENT_LABELS = (SentimentLabel.NEGATIVE, SentimentLabel.HIGHLY_NEGATIVE)
MEANINGFUL_CUSTOMER_IMPACT_LEVELS = ("high", "critical")
CRITICAL_CUSTOMER_IMPACT_LEVELS = ("critical",)
SENTIMENT_EVIDENCE_WEIGHT = 12
CUSTOMER_IMPACT_EVIDENCE_WEIGHT = 12


class CustomerCommunicationRule(RecommendationRule):
    """
    Customer Communication Rule

    Fires when customer sentiment has deteriorated to negative or highly
    negative, or the business impact's customer dimension is high or
    critical -- either signal means customers are likely to notice or are
    already reacting, warranting proactive communication.
    """

    def evaluate(self, context: IntelligenceContext) -> Tuple[Recommendation, ...]:
        nlp = context.nlp_intelligence
        negative_sentiment = nlp is not None and nlp.sentiment_label in NEGATIVE_SENTIMENT_LABELS
        customer_impact_meaningful = context.business_impact.customer_impact in MEANINGFUL_CUSTOMER_IMPACT_LEVELS

        if not negative_sentiment and not customer_impact_meaningful:
            return ()

        evidence: List[SupportingEvidence] = []
        if negative_sentiment:
            evidence.append(
                SupportingEvidence(
                    source=EvidenceSource.NLP_INTELLIGENCE,
                    description=f"Customer sentiment is {nlp.sentiment_label.value}",
                    weight=SENTIMENT_EVIDENCE_WEIGHT,
                )
            )
        if customer_impact_meaningful:
            evidence.append(
                SupportingEvidence(
                    source=EvidenceSource.BUSINESS_IMPACT,
                    description=f"Business impact customer dimension is {context.business_impact.customer_impact}",
                    weight=CUSTOMER_IMPACT_EVIDENCE_WEIGHT,
                )
            )

        highly_urgent = (nlp is not None and nlp.sentiment_label == SentimentLabel.HIGHLY_NEGATIVE) or (
            context.business_impact.customer_impact in CRITICAL_CUSTOMER_IMPACT_LEVELS
        )
        priority = RecommendationPriority.HIGH if highly_urgent else RecommendationPriority.MEDIUM
        score = scoring.compute_score(priority, evidence)

        return (
            Recommendation(
                incident_id=context.incident.incident_id,
                category=RecommendationCategory.CUSTOMER_COMMUNICATION,
                action="Issue proactive customer communication acknowledging the issue and expected resolution timeline.",
                priority=priority,
                score=score,
                rationale="Customer-facing signals indicate customers are affected and should be proactively informed.",
                priority_rationale=(
                    "Highly negative sentiment or critical customer impact warrants high urgency; "
                    "otherwise medium urgency applies."
                ),
                supporting_evidence=tuple(evidence),
            ),
        )
