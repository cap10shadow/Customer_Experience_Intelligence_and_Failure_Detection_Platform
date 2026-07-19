from backend.services.nlp_service.app.services.keyword_extractor import KeywordExtractor


def test_removes_stopwords_and_punctuation():
    keywords = KeywordExtractor.extract("The delivery, was late and the package was damaged!")
    assert "the" not in keywords
    assert "and" not in keywords
    assert "delivery" in keywords
    assert "damaged" in keywords


def test_deduplicates_tokens():
    keywords = KeywordExtractor.extract("broken broken broken product")
    assert keywords.count("broken") == 1


def test_filters_short_tokens():
    keywords = KeywordExtractor.extract("it is ok to go up")
    assert all(len(k) > 2 for k in keywords)


def test_limits_to_twenty_keywords():
    text = " ".join(f"keyword{i}" for i in range(30))
    keywords = KeywordExtractor.extract(text)
    assert len(keywords) == 20
