import re
from typing import Tuple, List

from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel
from backend.services.nlp_service.app.utils.constants import (
    SENTIMENT_KEYWORDS,
    URGENCY_KEYWORDS,
    ISSUE_CATEGORY_KEYWORDS
)


def _find_matches(text: str, keywords: List[str]) -> List[str]:
    """Helper to find matching keywords in text."""
    matches = []
    text_lower = text.lower()
    for kw in keywords:
        # Use simple word boundary matching
        if re.search(rf"\b{re.escape(kw.lower())}\b", text_lower):
            matches.append(kw)
    return matches


class SentimentClassifier:
    """Deterministic sentiment classifier based on operational keywords."""
    
    @staticmethod
    def classify(text: str) -> Tuple[SentimentLabel, List[str]]:
        """
        Classifies sentiment and returns the matched keywords.
        Priority: Highly Negative -> Negative -> Positive -> Neutral.
        """
        highly_negative_matches = _find_matches(text, SENTIMENT_KEYWORDS[SentimentLabel.HIGHLY_NEGATIVE])
        if highly_negative_matches:
            return SentimentLabel.HIGHLY_NEGATIVE, highly_negative_matches
            
        negative_matches = _find_matches(text, SENTIMENT_KEYWORDS[SentimentLabel.NEGATIVE])
        if negative_matches:
            return SentimentLabel.NEGATIVE, negative_matches
            
        positive_matches = _find_matches(text, SENTIMENT_KEYWORDS[SentimentLabel.POSITIVE])
        if positive_matches:
            return SentimentLabel.POSITIVE, positive_matches
            
        neutral_matches = _find_matches(text, SENTIMENT_KEYWORDS[SentimentLabel.NEUTRAL])
        return SentimentLabel.NEUTRAL, neutral_matches


class UrgencyClassifier:
    """Deterministic urgency classifier based on escalation keywords."""
    
    @staticmethod
    def classify(text: str) -> Tuple[UrgencyLabel, List[str]]:
        """
        Classifies urgency and returns the matched keywords.
        Priority: Critical -> High -> Medium -> Low.
        """
        critical_matches = _find_matches(text, URGENCY_KEYWORDS[UrgencyLabel.CRITICAL])
        if critical_matches:
            return UrgencyLabel.CRITICAL, critical_matches
            
        high_matches = _find_matches(text, URGENCY_KEYWORDS[UrgencyLabel.HIGH])
        if high_matches:
            return UrgencyLabel.HIGH, high_matches
            
        medium_matches = _find_matches(text, URGENCY_KEYWORDS[UrgencyLabel.MEDIUM])
        if medium_matches:
            return UrgencyLabel.MEDIUM, medium_matches
            
        low_matches = _find_matches(text, URGENCY_KEYWORDS[UrgencyLabel.LOW])
        return UrgencyLabel.LOW, low_matches


class IssueCategorizer:
    """Deterministic issue categorizer based on problem domain keywords."""
    
    @staticmethod
    def categorize(text: str) -> Tuple[IssueCategory, List[str]]:
        """
        Categorizes issue and returns matched keywords.
        Returns the category with the most keyword matches.
        Falls back to OPERATIONAL_FAILURE if no clear match.
        """
        best_category = IssueCategory.OPERATIONAL_FAILURE
        max_matches = 0
        all_matches = []
        
        for category, keywords in ISSUE_CATEGORY_KEYWORDS.items():
            matches = _find_matches(text, keywords)
            if matches:
                all_matches.extend(matches)
                if len(matches) > max_matches:
                    max_matches = len(matches)
                    best_category = category
                    
        return best_category, list(set(all_matches))
