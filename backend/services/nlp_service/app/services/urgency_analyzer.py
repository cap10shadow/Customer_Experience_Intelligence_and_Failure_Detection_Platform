from typing import List, Tuple

from backend.shared.constants.enums.complaint import UrgencyLabel
from backend.services.nlp_service.app.utils.constants import URGENCY_KEYWORDS
from backend.services.nlp_service.app.utils.keyword_matching import find_keyword_matches


class UrgencyAnalyzer:
    """Deterministic urgency classifier based on escalation keywords."""

    @staticmethod
    def classify(text: str) -> Tuple[UrgencyLabel, List[str]]:
        """
        Classifies urgency and returns the matched keywords.
        Priority: Critical -> High -> Medium -> Low.
        """
        critical_matches = find_keyword_matches(text, URGENCY_KEYWORDS[UrgencyLabel.CRITICAL])
        if critical_matches:
            return UrgencyLabel.CRITICAL, critical_matches

        high_matches = find_keyword_matches(text, URGENCY_KEYWORDS[UrgencyLabel.HIGH])
        if high_matches:
            return UrgencyLabel.HIGH, high_matches

        medium_matches = find_keyword_matches(text, URGENCY_KEYWORDS[UrgencyLabel.MEDIUM])
        if medium_matches:
            return UrgencyLabel.MEDIUM, medium_matches

        low_matches = find_keyword_matches(text, URGENCY_KEYWORDS[UrgencyLabel.LOW])
        return UrgencyLabel.LOW, low_matches
