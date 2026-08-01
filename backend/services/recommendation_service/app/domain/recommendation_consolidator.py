from typing import Dict, Iterable, List, Sequence, Tuple

from backend.services.recommendation_service.app.domain import scoring
from backend.services.recommendation_service.app.domain.precedence import category_precedence_index, priority_rank
from backend.services.recommendation_service.app.domain.recommendation import Recommendation
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence

# The one conflict this Step 1 domain engine resolves: MONITOR ("no active
# response needed") is contradictory guidance alongside any of these
# genuinely urgent categories for the same incident. Categories not listed
# here (INVESTIGATE, CUSTOMER_COMMUNICATION, OPERATIONAL_ACTION) are
# compatible with MONITOR -- e.g. an operator can monitor an incident while
# it is independently being investigated, so MONITOR is not dropped for
# those combinations.
MONITOR_CONFLICTS_WITH: Tuple[RecommendationCategory, ...] = (
    RecommendationCategory.ESCALATE,
    RecommendationCategory.MITIGATE,
    RecommendationCategory.SLA_PROTECTION,
    RecommendationCategory.INFRASTRUCTURE_ACTION,
)


class RecommendationConsolidator:
    """
    Recommendation Consolidator (Domain Service)

    Operational Purpose:
    Consumes the raw Recommendations produced by every Recommendation Rule
    and produces the final, optimized Recommendation collection: duplicates
    removed, equivalent recommendations merged, conflicting recommendations
    resolved, and the result deterministically ordered.

    Architectural Boundaries:
    - Never creates a new Recommendation from nothing -- every Recommendation
      it returns originated from a rule's own output (an unmodified raw
      Recommendation, or a merge of two-or-more raw Recommendations that
      were themselves rule-produced). It only refines what rules already
      produced.
    - When merging equivalent Recommendations, the merged score is still
      computed via the shared Recommendation Scoring Policy
      (`scoring.compute_score`), from the union of both recommendations'
      supporting evidence -- never an ad-hoc average/max of the pre-merge
      scores. This keeps "every score is policy-derived" true even after
      consolidation, not just at rule-evaluation time.
    - Ordering is deterministic and total: Priority, then Recommendation
      Category Precedence, then Recommendation Score (descending), then
      Rule Evaluation Order -- the last tiebreak falls out naturally from
      Python's stable sort applied to a list already in rule-evaluation
      order, with no extra bookkeeping required.
    """

    def consolidate(self, raw_recommendations: Sequence[Recommendation]) -> Tuple[Recommendation, ...]:
        deduplicated = self._remove_exact_duplicates(raw_recommendations)
        merged = self._merge_equivalent(deduplicated)
        resolved = self._resolve_conflicts(merged)
        return self._order(resolved)

    @staticmethod
    def _remove_exact_duplicates(recommendations: Sequence[Recommendation]) -> Tuple[Recommendation, ...]:
        """Removes field-for-field identical Recommendations, keeping the first occurrence of each."""
        seen: List[Recommendation] = []
        for recommendation in recommendations:
            if recommendation not in seen:
                seen.append(recommendation)
        return tuple(seen)

    @staticmethod
    def _merge_equivalent(recommendations: Sequence[Recommendation]) -> Tuple[Recommendation, ...]:
        """
        Merges Recommendations that share the same (category, action) --
        the same real-world action, independently recommended by more than
        one rule with possibly different priority/evidence/rationale --
        into one Recommendation carrying the union of their evidence and
        the more urgent of their priorities.
        """
        groups: Dict[Tuple[RecommendationCategory, str], List[Recommendation]] = {}
        group_order: List[Tuple[RecommendationCategory, str]] = []
        for recommendation in recommendations:
            key = (recommendation.category, recommendation.action)
            if key not in groups:
                groups[key] = []
                group_order.append(key)
            groups[key].append(recommendation)

        merged: List[Recommendation] = []
        for key in group_order:
            group = groups[key]
            merged.append(group[0] if len(group) == 1 else RecommendationConsolidator._merge_group(group))
        return tuple(merged)

    @staticmethod
    def _merge_group(group: Sequence[Recommendation]) -> Recommendation:
        best_priority = min(group, key=lambda recommendation: priority_rank(recommendation.priority)).priority
        combined_evidence = RecommendationConsolidator._deduplicate_evidence(
            evidence for recommendation in group for evidence in recommendation.supporting_evidence
        )
        merged_score = scoring.compute_score(best_priority, combined_evidence)
        first = group[0]

        return Recommendation(
            incident_id=first.incident_id,
            category=first.category,
            action=first.action,
            priority=best_priority,
            score=merged_score,
            rationale=RecommendationConsolidator._combine_text(recommendation.rationale for recommendation in group),
            priority_rationale=RecommendationConsolidator._combine_text(
                recommendation.priority_rationale for recommendation in group
            ),
            supporting_evidence=combined_evidence,
        )

    @staticmethod
    def _deduplicate_evidence(evidence: Iterable[SupportingEvidence]) -> Tuple[SupportingEvidence, ...]:
        seen: List[SupportingEvidence] = []
        for item in evidence:
            if item not in seen:
                seen.append(item)
        return tuple(seen)

    @staticmethod
    def _combine_text(texts: Iterable[str]) -> str:
        """Joins distinct, non-empty strings in encounter order -- identical text across a merge group is not repeated."""
        return " ".join(dict.fromkeys(text for text in texts if text))

    @staticmethod
    def _resolve_conflicts(recommendations: Sequence[Recommendation]) -> Tuple[Recommendation, ...]:
        """
        Drops MONITOR whenever it co-occurs with a genuinely more urgent
        category for the same consolidation run (see `MONITOR_CONFLICTS_WITH`).
        No other category pair is treated as conflicting -- every other
        combination represents complementary, not contradictory, guidance.
        """
        categories_present = {recommendation.category for recommendation in recommendations}
        monitor_should_be_dropped = RecommendationCategory.MONITOR in categories_present and any(
            category in categories_present for category in MONITOR_CONFLICTS_WITH
        )
        if not monitor_should_be_dropped:
            return tuple(recommendations)
        return tuple(
            recommendation for recommendation in recommendations if recommendation.category != RecommendationCategory.MONITOR
        )

    @staticmethod
    def _order(recommendations: Sequence[Recommendation]) -> Tuple[Recommendation, ...]:
        """Priority -> Category Precedence -> Score (descending) -> Rule Evaluation Order (stable-sort tiebreak)."""
        return tuple(
            sorted(
                recommendations,
                key=lambda recommendation: (
                    priority_rank(recommendation.priority),
                    category_precedence_index(recommendation.category),
                    -recommendation.score,
                ),
            )
        )
