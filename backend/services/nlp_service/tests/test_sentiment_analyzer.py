from backend.services.nlp_service.app.services.sentiment_analyzer import SentimentAnalyzer
from backend.shared.constants.enums.complaint import SentimentLabel


def test_classifies_highly_negative():
    label, matches = SentimentAnalyzer.classify("This is unacceptable, I will sue you for fraud.")
    assert label == SentimentLabel.HIGHLY_NEGATIVE
    assert "unacceptable" in matches
    assert "fraud" in matches


def test_classifies_negative():
    label, matches = SentimentAnalyzer.classify("I am frustrated, the order was delayed.")
    assert label == SentimentLabel.NEGATIVE
    assert "frustrated" in matches


def test_classifies_positive():
    label, matches = SentimentAnalyzer.classify("Thanks, the support was great and fast.")
    assert label == SentimentLabel.POSITIVE
    assert "great" in matches


def test_classifies_neutral_when_no_keywords_match():
    label, matches = SentimentAnalyzer.classify("The package arrived on Tuesday.")
    assert label == SentimentLabel.NEUTRAL
    assert matches == []


def test_highly_negative_takes_priority_over_positive():
    label, _ = SentimentAnalyzer.classify("It was great at first but now this is a scam.")
    assert label == SentimentLabel.HIGHLY_NEGATIVE
