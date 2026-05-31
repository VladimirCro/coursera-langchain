"""
LEGACY FEEDBACK ANALYZER
This represents typical legacy LLM code with multiple maintenance issues
"""

import openai

# ISSUE #1: Hardcoded API key - security risk
openai.api_key = "sk-proj-abc123def456..."  # Hardcoded key

def analyze_customer_feedback(feedback_text):
    """Analyze customer feedback and return sentiment + category"""
    
    # ISSUE #2: Hardcoded prompt embedded in function
    sentiment_prompt = f"""Rate the sentiment of this customer feedback on a scale of 1-5 
where 1=very negative, 5=very positive. Just respond with the number.

Feedback: {feedback_text}"""
    
    # Get sentiment using GPT-3.5
    # ISSUE #3: Bare except clause - catches all errors silently
    try:
        sentiment_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # ISSUE #4: Using GPT-3.5 here
            messages=[{"role": "user", "content": sentiment_prompt}]
        )
        sentiment_score = sentiment_response.choices[0].message.content.strip()
    except:
        sentiment_score = "3"  # Default to neutral - no logging!
    
    # ISSUE #2: Another hardcoded prompt
    category_prompt = f"""Categorize this customer feedback into one of these categories: 
Product, Service, or Billing. Respond with just the category name.

Feedback: {feedback_text}"""
    
    # Get category using GPT-4
    # ISSUE #3: Another bare except clause
    try:
        category_response = openai.ChatCompletion.create(
            model="gpt-4",  # ISSUE #4: Using GPT-4 here - inconsistent!
            messages=[{"role": "user", "content": category_prompt}]
        )
        category = category_response.choices[0].message.content.strip()
    except:
        category = "Product"  # Default - no error visibility
    
    # ISSUE #5: Brittle string parsing - just hoping for right format
    return {
        "sentiment": sentiment_score,
        "category": category
    }

# ISSUE #6: No test coverage whatsoever

if __name__ == "__main__":
    # Example usage
    test_feedback = "The new dashboard is confusing and slow to load"
    result = analyze_customer_feedback(test_feedback)
    print(f"Sentiment: {result['sentiment']}")
    print(f"Category: {result['category']}")