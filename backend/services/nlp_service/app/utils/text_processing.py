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
        # Normalize and remove punctuation
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        tokens = clean_text.split()
        
        # Filter stopwords and short tokens
        keywords = []
        seen = set()
        for token in tokens:
            if token not in OPERATIONAL_STOPWORDS and len(token) > 2 and token not in seen:
                keywords.append(token)
                seen.add(token)
                
        # Limit to top 20 keywords for operational sanity
        return keywords[:20]


class Summarizer:
    """Lightweight deterministic summarization."""
    
    @staticmethod
    def summarize(text: str) -> str:
        """
        Extractive rule-based summarization.
        Returns the first two sentences to act as an operational summary.
        """
        if not text:
            return ""
            
        # Split by common sentence terminators (. ! ?)
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return ""
            
        # Take up to the first two sentences
        summary = " ".join(sentences[:2])
        
        # Truncate if insanely long (e.g., someone didn't use punctuation)
        if len(summary) > 250:
            return summary[:247] + "..."
            
        return summary
