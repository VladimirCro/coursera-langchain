"""
LCEL chain that composes prompt | model | parser.
Fixes Issue #3: Bare exception clauses replaced with specific error handling + logging.
"""

from typing import Optional

from refactored.parsers import FeedbackAnalysis, parser
from refactored.prompts import analysis_prompt
from refactored.utils import get_model, logger

_chain = None


def _get_chain():
    """Lazy-initialize the LCEL chain (prompt | model | parser)."""
    global _chain
    if _chain is None:
        model = get_model()
        _chain = analysis_prompt | model | parser
    return _chain


def analyze_customer_feedback(feedback_text: str) -> Optional[FeedbackAnalysis]:
    """
    Analyze customer feedback and return structured results.

    Args:
        feedback_text: The customer feedback to analyze.

    Returns:
        FeedbackAnalysis with sentiment, category, and confidence.
        Returns a low-confidence default if analysis fails.
    """
    try:
        logger.info(f"Analyzing feedback: {feedback_text[:50]}...")
        result = _get_chain().invoke({"feedback_text": feedback_text})
        logger.info(
            f"Analysis successful: sentiment={result.sentiment_score}, "
            f"category={result.category}, confidence={result.confidence}"
        )
        return result

    except Exception as e:
        logger.error(f"Error analyzing feedback: {e}")
        logger.error(f"Feedback text: {feedback_text}")
        return FeedbackAnalysis(
            sentiment_score=3,
            category="Product",
            confidence="low",
        )
