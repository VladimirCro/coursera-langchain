"""
Refactored Feedback Analyzer - Modular LangChain Architecture
=============================================================
Organized into:
  prompts/   - Externalized PromptTemplate definitions
  parsers/   - Pydantic models and OutputParser
  chains/    - LCEL chains composing prompt | model | parser
  utils/     - Configuration, logging, and model factory
"""

from refactored.chains import analyze_customer_feedback
from refactored.parsers import FeedbackAnalysis

__all__ = ["analyze_customer_feedback", "FeedbackAnalysis"]
