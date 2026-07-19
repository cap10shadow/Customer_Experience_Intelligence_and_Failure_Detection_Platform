import re
from typing import List

from backend.services.nlp_service.app.utils.constants import OPERATIONAL_STOPWORDS


class KeywordExtractor:
    """Extracts operational keywords deterministically."""

    @staticmethod
    def extract(text: str) -> List[str]:
        """
        Tokenizes text, normalizes to lowercase, removes punctuation and stopwords.
        Returns a deduplicated list of operational tokens.
        """
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        tokens = clean_text.split()

        keywords = []
        seen = set()
        for token in tokens:
            if token not in OPERATIONAL_STOPWORDS and len(token) > 2 and token not in seen:
                keywords.append(token)
                seen.add(token)

        # Limit to top 20 keywords for operational sanity
        return keywords[:20]
