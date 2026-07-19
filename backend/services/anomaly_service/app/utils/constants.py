from typing import Dict

from backend.shared.constants.enums.complaint import SentimentLabel

# Ordinal scale used only to average an already-classified sentiment label
# over time. This is *not* sentiment recomputation — the label itself was
# produced once by the NLP service; this mapping merely lets the Trend
# Engine express a categorical distribution as a single trend-friendly number.
SENTIMENT_SCORES: Dict[SentimentLabel, int] = {
    SentimentLabel.HIGHLY_NEGATIVE: -2,
    SentimentLabel.NEGATIVE: -1,
    SentimentLabel.NEUTRAL: 0,
    SentimentLabel.POSITIVE: 1,
}
