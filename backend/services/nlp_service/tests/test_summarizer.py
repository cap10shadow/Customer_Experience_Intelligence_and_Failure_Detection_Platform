from backend.services.nlp_service.app.services.summarizer import Summarizer


def test_returns_first_two_sentences():
    text = "The product arrived broken. Support was unhelpful. I want a refund."
    summary = Summarizer.summarize(text)
    assert summary == "The product arrived broken. Support was unhelpful."


def test_returns_empty_string_for_empty_input():
    assert Summarizer.summarize("") == ""


def test_returns_single_sentence_when_only_one_exists():
    summary = Summarizer.summarize("Everything was fine.")
    assert summary == "Everything was fine."


def test_truncates_overly_long_summary():
    long_text = "word " * 100  # no punctuation, single "sentence"
    summary = Summarizer.summarize(long_text)
    assert len(summary) == 250
    assert summary.endswith("...")
