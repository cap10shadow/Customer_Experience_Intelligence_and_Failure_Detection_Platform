from typing import List, Tuple

from backend.shared.constants.enums.complaint import IssueCategory
from backend.services.nlp_service.app.utils.constants import ISSUE_CATEGORY_KEYWORDS
from backend.services.nlp_service.app.utils.keyword_matching import find_keyword_matches


class CategoryClassifier:
    """Deterministic issue categorizer based on problem domain keywords."""

    @staticmethod
    def classify(text: str) -> Tuple[IssueCategory, List[str]]:
        """
        Categorizes issue and returns matched keywords.
        Returns the category with the most keyword matches.
        Falls back to OPERATIONAL_FAILURE if no clear match.
        """
        best_category = IssueCategory.OPERATIONAL_FAILURE
        max_matches = 0
        all_matches = []

        for category, keywords in ISSUE_CATEGORY_KEYWORDS.items():
            matches = find_keyword_matches(text, keywords)
            if matches:
                all_matches.extend(matches)
                if len(matches) > max_matches:
                    max_matches = len(matches)
                    best_category = category

        return best_category, list(set(all_matches))
