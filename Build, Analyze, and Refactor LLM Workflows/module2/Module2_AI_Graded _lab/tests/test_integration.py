"""
INTEGRATION TESTS - Test the full chain with the OpenAI API.
These tests require a valid OPENAI_API_KEY environment variable.
"""

import os

import pytest

from refactored.chains import analyze_customer_feedback
from refactored.parsers import FeedbackAnalysis


@pytest.fixture(autouse=True)
def require_api_key():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")


# =============================================================================
# Sentiment Range Tests
# =============================================================================

class TestSentimentRange:
    def test_negative_feedback(self):
        result = analyze_customer_feedback(
            "This product is terrible and doesn't work at all! Worst purchase ever."
        )
        assert isinstance(result, FeedbackAnalysis)
        assert result.sentiment_score <= 2

    def test_positive_feedback(self):
        result = analyze_customer_feedback(
            "Amazing product! Exceeded all my expectations. Highly recommend!"
        )
        assert isinstance(result, FeedbackAnalysis)
        assert result.sentiment_score >= 4

    def test_neutral_feedback(self):
        result = analyze_customer_feedback(
            "The product is okay. Some features work well, others could be better."
        )
        assert isinstance(result, FeedbackAnalysis)
        assert result.sentiment_score == 3


# =============================================================================
# Category Classification Tests
# =============================================================================

class TestCategoryClassification:
    def test_service_category(self):
        result = analyze_customer_feedback(
            "The customer support team was incredibly helpful and responsive"
        )
        assert result.category == "Service"

    def test_billing_category(self):
        result = analyze_customer_feedback(
            "I was charged twice for the same transaction on my invoice"
        )
        assert result.category == "Billing"

    def test_product_category(self):
        result = analyze_customer_feedback(
            "The new dashboard is confusing and slow to load"
        )
        assert result.category == "Product"


# =============================================================================
# Output Structure Validation
# =============================================================================

class TestOutputStructure:
    def test_all_fields_present(self):
        result = analyze_customer_feedback("The product is okay, nothing special")
        assert hasattr(result, "sentiment_score")
        assert hasattr(result, "category")
        assert hasattr(result, "confidence")

    def test_field_types(self):
        result = analyze_customer_feedback("Great service, very happy")
        assert isinstance(result.sentiment_score, int)
        assert isinstance(result.category, str)
        assert isinstance(result.confidence, str)

    def test_sentiment_in_valid_range(self):
        result = analyze_customer_feedback("Average experience overall")
        assert 1 <= result.sentiment_score <= 5

    def test_category_is_valid(self):
        result = analyze_customer_feedback("The billing department was slow")
        assert result.category in ["Product", "Service", "Billing"]

    def test_confidence_is_valid(self):
        result = analyze_customer_feedback("Absolutely love this product!")
        assert result.confidence in ["high", "medium", "low"]


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    def test_empty_feedback_returns_result(self):
        result = analyze_customer_feedback("")
        assert result is not None
        assert isinstance(result, FeedbackAnalysis)

    def test_very_long_feedback(self):
        long_feedback = "The product is great. " * 100
        result = analyze_customer_feedback(long_feedback)
        assert result is not None


# =============================================================================
# Behavioral Equivalence (refactored vs legacy expectations)
# =============================================================================

class TestBehavioralEquivalence:
    """Verify refactored output matches legacy behavior for known inputs."""

    def test_negative_product_feedback(self):
        result = analyze_customer_feedback("Terrible experience, nothing worked")
        assert result.sentiment_score <= 2
        assert result.category in ["Product", "Service"]

    def test_positive_product_feedback(self):
        result = analyze_customer_feedback("Great product, very satisfied")
        assert result.sentiment_score >= 4
        assert result.category == "Product"
