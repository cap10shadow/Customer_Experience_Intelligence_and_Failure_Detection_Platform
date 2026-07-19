from backend.services.nlp_service.app.services.urgency_analyzer import UrgencyAnalyzer
from backend.shared.constants.enums.complaint import UrgencyLabel


def test_classifies_critical():
    label, matches = UrgencyAnalyzer.classify("This is a safety issue, someone got injured.")
    assert label == UrgencyLabel.CRITICAL
    assert "safety" in matches


def test_classifies_high():
    label, matches = UrgencyAnalyzer.classify("Please escalate this to a manager asap.")
    assert label == UrgencyLabel.HIGH
    assert "escalate" in matches


def test_classifies_medium():
    label, matches = UrgencyAnalyzer.classify("Still waiting on my delayed order.")
    assert label == UrgencyLabel.MEDIUM
    assert "waiting" in matches


def test_classifies_low_when_no_keywords_match():
    label, matches = UrgencyAnalyzer.classify("Just leaving some general feedback.")
    assert label == UrgencyLabel.LOW


def test_critical_takes_priority_over_high():
    label, _ = UrgencyAnalyzer.classify("Please escalate immediately, this is a safety hazard.")
    assert label == UrgencyLabel.CRITICAL
