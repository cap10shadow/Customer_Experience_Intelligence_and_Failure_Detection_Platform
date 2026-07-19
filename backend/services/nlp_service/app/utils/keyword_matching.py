import re
from typing import List


def find_keyword_matches(text: str, keywords: List[str]) -> List[str]:
    """
    Returns the subset of `keywords` that appear in `text` as whole words.
    Shared by the deterministic classifiers (sentiment, urgency, category)
    so keyword-boundary matching behaves identically across the pipeline.
    """
    matches = []
    text_lower = text.lower()
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw.lower())}\b", text_lower):
            matches.append(kw)
    return matches
