from backend.services.nlp_service.app.services.category_classifier import CategoryClassifier
from backend.shared.constants.enums.complaint import IssueCategory


def test_classifies_delivery_issue():
    category, matches = CategoryClassifier.classify("My package shipping was late and tracking shows lost.")
    assert category == IssueCategory.DELIVERY_ISSUE
    assert "shipping" in matches


def test_classifies_payment_issue():
    category, matches = CategoryClassifier.classify("I was double charged and the billing invoice is wrong.")
    assert category == IssueCategory.PAYMENT_ISSUE
    assert "billing" in matches


def test_falls_back_to_operational_failure_when_no_match():
    category, matches = CategoryClassifier.classify("Hello there, just saying hi.")
    assert category == IssueCategory.OPERATIONAL_FAILURE
    assert matches == []


def test_returns_category_with_most_keyword_matches():
    # Two product-issue keywords vs one delivery-issue keyword.
    category, _ = CategoryClassifier.classify("The product quality is broken and damaged, delivery was fine.")
    assert category == IssueCategory.PRODUCT_ISSUE
