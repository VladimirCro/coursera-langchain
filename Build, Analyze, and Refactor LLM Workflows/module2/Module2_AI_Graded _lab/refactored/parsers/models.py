"""
Pydantic output models and parsers for feedback analysis.
Replaces brittle string parsing from legacy system (Issue #5).
"""

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class FeedbackAnalysis(BaseModel):
    """Structured output for feedback analysis."""
    sentiment_score: int = Field(
        description="Sentiment score from 1-5 where 1=very negative, 5=very positive",
        ge=1,
        le=5,
    )
    category: str = Field(
        description="Category: Product, Service, or Billing",
    )
    confidence: str = Field(
        description="Confidence level: high, medium, or low",
    )


parser = PydanticOutputParser(pydantic_object=FeedbackAnalysis)
