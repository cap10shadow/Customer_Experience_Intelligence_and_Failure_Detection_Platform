import re


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

        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return ""

        summary = " ".join(sentences[:2])

        # Truncate if insanely long (e.g., someone didn't use punctuation)
        if len(summary) > 250:
            return summary[:247] + "..."

        return summary
