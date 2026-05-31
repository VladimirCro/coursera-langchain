"""
Externalized prompt templates for feedback analysis.
Fixes Issue #2: Hardcoded prompts embedded in function bodies.
Consolidates two separate prompts (sentiment + category) into one (50% cost savings).
"""

from langchain_core.prompts import PromptTemplate

from refactored.parsers.models import parser

analysis_prompt = PromptTemplate(
    template="""You are a customer feedback analyst.

Analyze the following customer feedback and provide:
1. Sentiment score (1-5, where 1=very negative, 5=very positive)
2. Category (choose one: Product, Service, or Billing)
3. Confidence level (high, medium, or low) based on clarity of the feedback

Feedback: {feedback_text}

{format_instructions}""",
    input_variables=["feedback_text"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)
