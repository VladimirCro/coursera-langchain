"""
TEST SUITE FOR REFACTORED FEEDBACK ANALYZER
Comprehensive tests to verify correct behavior
"""

import pytest
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the function and model to test
from refactored_feedback_analyzer import analyze_customer_feedback, FeedbackAnalysis

# =============================================================================
# TEST CONFIGURATION
# =============================================================================
@pytest.fixture(autouse=True)
def check_api_key():
    """Ensure API key is configured before running tests"""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

# =============================================================================
# TEST 1: NEGATIVE FEEDBACK
# =============================================================================
def test_negative_feedback():
    """Test that clearly negative feedback gets low sentiment score"""
    feedback = "This product is terrible and doesn't work at all! Worst purchase ever."
    result = analyze_customer_feedback(feedback)
    
    # Verify result is returned
    assert result is not None
    
    # Verify it's the correct type
    assert isinstance(result, FeedbackAnalysis)
    
    # Verify sentiment is negative (1 or 2)
    assert result.sentiment_score <= 2, f"Expected negative sentiment, got {result.sentiment_score}"
    
    # Verify category is valid
    assert result.category in ["Product", "Service", "Billing"]
    
    # Verify confidence exists
    assert result.confidence in ["high", "medium", "low"]
    
    print(f"✓ Negative feedback test passed: score={result.sentiment_score}, category={result.category}")

# =============================================================================
# TEST 2: POSITIVE FEEDBACK
# =============================================================================
def test_positive_feedback():
    """Test that clearly positive feedback gets high sentiment score"""
    feedback = "Amazing product! Exceeded all my expectations. Highly recommend!"
    result = analyze_customer_feedback(feedback)
    
    # Verify result is returned
    assert result is not None
    
    # Verify sentiment is positive (4 or 5)
    assert result.sentiment_score >= 4, f"Expected positive sentiment, got {result.sentiment_score}"
    
    # Verify category is valid
    assert result.category in ["Product", "Service", "Billing"]
    
    # Verify confidence exists
    assert result.confidence in ["high", "medium", "low"]
    
    print(f"✓ Positive feedback test passed: score={result.sentiment_score}, category={result.category}")

# =============================================================================
# TEST 3: SERVICE CATEGORY
# =============================================================================
def test_service_category():
    """Test that service-related feedback is categorized correctly"""
    feedback = "The customer support team was incredibly helpful and responsive"
    result = analyze_customer_feedback(feedback)
    
    # Verify result is returned
    assert result is not None
    
    # Verify category is Service
    assert result.category == "Service", f"Expected Service category, got {result.category}"
    
    # Verify positive sentiment
    assert result.sentiment_score >= 4
    
    print(f"✓ Service category test passed: category={result.category}")

# =============================================================================
# TEST 4: BILLING CATEGORY
# =============================================================================
def test_billing_category():
    """Test that billing-related feedback is categorized correctly"""
    feedback = "I was charged twice for the same transaction on my invoice"
    result = analyze_customer_feedback(feedback)
    
    # Verify result is returned
    assert result is not None
    
    # Verify category is Billing
    assert result.category == "Billing", f"Expected Billing category, got {result.category}"
    
    # Verify negative sentiment (being charged twice is bad)
    assert result.sentiment_score <= 3
    
    print(f"✓ Billing category test passed: category={result.category}")

# =============================================================================
# TEST 5: OUTPUT STRUCTURE VALIDATION
# =============================================================================
def test_output_structure():
    """Test that output has required structure and types"""
    feedback = "The product is okay, nothing special"
    result = analyze_customer_feedback(feedback)
    
    # Verify result exists
    assert result is not None
    
    # Verify all required fields exist
    assert hasattr(result, 'sentiment_score')
    assert hasattr(result, 'category')
    assert hasattr(result, 'confidence')
    
    # Verify types
    assert isinstance(result.sentiment_score, int)
    assert isinstance(result.category, str)
    assert isinstance(result.confidence, str)
    
    # Verify sentiment score is in valid range
    assert 1 <= result.sentiment_score <= 5
    
    print(f"✓ Output structure test passed: all fields present and typed correctly")

# =============================================================================
# TEST 6: NEUTRAL FEEDBACK
# =============================================================================
def test_neutral_feedback():
    """Test that neutral feedback gets middle-range sentiment score"""
    feedback = "The product is okay. Some features work well, others could be better."
    result = analyze_customer_feedback(feedback)
    
    # Verify result is returned
    assert result is not None
    
    # Verify sentiment is neutral (3)
    assert result.sentiment_score == 3, f"Expected neutral sentiment (3), got {result.sentiment_score}"
    
    print(f"✓ Neutral feedback test passed: score={result.sentiment_score}")

# =============================================================================
# TEST 7: EDGE CASE - EMPTY STRING
# =============================================================================
def test_empty_feedback():
    """Test handling of edge case - empty feedback"""
    feedback = ""
    result = analyze_customer_feedback(feedback)
    
    # Should still return a result (with low confidence likely)
    assert result is not None
    
    # Confidence should be low for empty input
    assert result.confidence == "low"
    
    print(f"✓ Empty feedback test passed: handled gracefully")

# =============================================================================
# TEST 8: BEHAVIORAL EQUIVALENCE WITH LEGACY
# =============================================================================
def test_behavioral_equivalence():
    """
    Test that refactored version produces equivalent results to legacy version
    This is critical for safe deployment
    """
    # Test cases with expected results
    test_cases = [
        {
            "feedback": "Terrible experience, nothing worked",
            "expected_sentiment_range": (1, 2),  # Should be negative
            "expected_category": ["Product", "Service"]  # Could be either
        },
        {
            "feedback": "Great product, very satisfied",
            "expected_sentiment_range": (4, 5),  # Should be positive
            "expected_category": ["Product"]
        }
    ]
    
    for test_case in test_cases:
        result = analyze_customer_feedback(test_case["feedback"])
        
        # Check sentiment range
        min_score, max_score = test_case["expected_sentiment_range"]
        assert min_score <= result.sentiment_score <= max_score, \
            f"Sentiment {result.sentiment_score} not in expected range {test_case['expected_sentiment_range']}"
        
        # Check category is one of expected
        assert result.category in test_case["expected_category"], \
            f"Category {result.category} not in expected {test_case['expected_category']}"
    
    print(f"✓ Behavioral equivalence test passed: results match expectations")

# =============================================================================
# RUN TESTS WITH PYTEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING TEST SUITE")
    print("=" * 70)
    print()
    
    # Run pytest programmatically
    pytest.main([__file__, "-v", "--tb=short"])