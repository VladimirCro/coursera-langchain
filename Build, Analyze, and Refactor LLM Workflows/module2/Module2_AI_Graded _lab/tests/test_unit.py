"""
UNIT TESTS - Test individual components in isolation.
Tests parsers, prompt templates, and model configuration.
"""

import pytest
from pydantic import ValidationError

from refactored.parsers.models import FeedbackAnalysis, parser
from refactored.prompts.templates import analysis_prompt


# =============================================================================
# Parser / Pydantic Model Tests
# =============================================================================

class TestFeedbackAnalysisModel:
    """Unit tests for the Pydantic output model."""

    def test_valid_input(self):
        result = FeedbackAnalysis(sentiment_score=4, category="Product", confidence="high")
        assert result.sentiment_score == 4
        assert result.category == "Product"
        assert result.confidence == "high"

    def test_sentiment_score_min_boundary(self):
        result = FeedbackAnalysis(sentiment_score=1, category="Service", confidence="low")
        assert result.sentiment_score == 1

    def test_sentiment_score_max_boundary(self):
        result = FeedbackAnalysis(sentiment_score=5, category="Billing", confidence="medium")
        assert result.sentiment_score == 5

    def test_sentiment_score_below_range_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackAnalysis(sentiment_score=0, category="Product", confidence="high")

    def test_sentiment_score_above_range_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackAnalysis(sentiment_score=6, category="Product", confidence="high")

    def test_all_categories_accepted(self):
        for cat in ["Product", "Service", "Billing"]:
            result = FeedbackAnalysis(sentiment_score=3, category=cat, confidence="medium")
            assert result.category == cat

    def test_all_confidence_levels(self):
        for conf in ["high", "medium", "low"]:
            result = FeedbackAnalysis(sentiment_score=3, category="Product", confidence=conf)
            assert result.confidence == conf

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            FeedbackAnalysis(sentiment_score=3, category="Product")  # missing confidence

    def test_model_serialization(self):
        result = FeedbackAnalysis(sentiment_score=2, category="Service", confidence="low")
        data = result.model_dump()
        assert data == {"sentiment_score": 2, "category": "Service", "confidence": "low"}


# =============================================================================
# Output Parser Tests
# =============================================================================

class TestOutputParser:
    """Unit tests for the PydanticOutputParser."""

    def test_parser_has_format_instructions(self):
        instructions = parser.get_format_instructions()
        assert "sentiment_score" in instructions
        assert "category" in instructions
        assert "confidence" in instructions

    def test_parser_type(self):
        assert parser.pydantic_object is FeedbackAnalysis


# =============================================================================
# Prompt Template Tests
# =============================================================================

class TestPromptTemplate:
    """Unit tests for the analysis prompt template."""

    def test_prompt_has_feedback_variable(self):
        assert "feedback_text" in analysis_prompt.input_variables

    def test_prompt_has_format_instructions(self):
        assert "format_instructions" in analysis_prompt.partial_variables

    def test_prompt_renders_correctly(self):
        rendered = analysis_prompt.format(feedback_text="Test feedback")
        assert "Test feedback" in rendered
        assert "sentiment_score" in rendered  # from format_instructions
        assert "Category" in rendered

    def test_prompt_contains_all_categories(self):
        rendered = analysis_prompt.format(feedback_text="x")
        assert "Product" in rendered
        assert "Service" in rendered
        assert "Billing" in rendered
