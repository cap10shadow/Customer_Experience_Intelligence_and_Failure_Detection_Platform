from typing import List, Tuple

from backend.shared.constants.enums.complaint import SentimentLabel
from backend.services.nlp_service.app.utils.constants import SENTIMENT_KEYWORDS
from backend.services.nlp_service.app.utils.keyword_matching import find_keyword_matches


class SentimentAnalyzer:
    """Deterministic sentiment classifier based on operational keywords."""

    @staticmethod
    def classify(text: str) -> Tuple[SentimentLabel, List[str]]:
        """
        Classifies sentiment and returns the matched keywords.
        Priority: Highly Negative -> Negative -> Positive -> Neutral.
        """
        highly_negative_matches = find_keyword_matches(text, SENTIMENT_KEYWORDS[SentimentLabel.HIGHLY_NEGATIVE])
        if highly_negative_matches:
            return SentimentLabel.HIGHLY_NEGATIVE, highly_negative_matches

        negative_matches = find_keyword_matches(text, SENTIMENT_KEYWORDS[SentimentLabel.NEGATIVE])
        if negative_matches:
            return SentimentLabel.NEGATIVE, negative_matches

        positive_matches = find_keyword_matches(text, SENTIMENT_KEYWORDS[SentimentLabel.POSITIVE])
        if positive_matches:
            return SentimentLabel.POSITIVE, positive_matches

        neutral_matches = find_keyword_matches(text, SENTIMENT_KEYWORDS[SentimentLabel.NEUTRAL])
        return SentimentLabel.NEUTRAL, neutral_matches
