"""
Legacy Intent Classifier - Customer Support System
===================================================
Original monolithic implementation (pre-LangChain refactoring).

Problems with this code:
- Hardcoded prompts scattered across 300+ lines
- Direct OpenAI API calls with no abstraction layer
- String/regex parsing of LLM responses (fragile)
- API key hardcoded / pulled from env inconsistently
- No configuration management - everything is magic strings
- Repeated boilerplate for every classification category
- Zero reusability - each function reimplements the same pattern
- No structured output validation
- Mixed concerns (API calls, parsing, business logic all together)
"""

import os
import re
import json
import openai

# -----------------------------------------------------------------------
# HARDCODED CONFIGURATION - scattered across the file
# -----------------------------------------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "sk-REPLACE_ME")
openai.api_key = OPENAI_API_KEY
MODEL_NAME = "gpt-3.5-turbo"
MAX_TOKENS = 512
TEMPERATURE = 0.0

# Hardcoded intent labels
VALID_INTENTS = [
    "billing",
    "technical_support",
    "account_management",
    "general_inquiry",
    "complaint",
    "escalation",
    "cancellation",
    "unknown",
]

# Hardcoded confidence thresholds
HIGH_CONFIDENCE = 0.85
MEDIUM_CONFIDENCE = 0.60
LOW_CONFIDENCE = 0.40


# -----------------------------------------------------------------------
# PRIMARY INTENT CLASSIFICATION - hardcoded prompt
# -----------------------------------------------------------------------
def classify_intent(user_message: str) -> dict:
    """
    Classify the intent of a customer support message.
    Returns a dict with intent, confidence, and reasoning.
    """
    # Hardcoded prompt - any change requires a code deployment
    prompt = f"""You are a customer support intent classifier.
Classify the following customer message into one of these intents:
- billing: questions about invoices, payments, charges, refunds
- technical_support: problems with product functionality, bugs, errors
- account_management: password resets, profile updates, account access
- general_inquiry: general questions about products or services
- complaint: expressing dissatisfaction or frustration
- escalation: requesting to speak to a manager or supervisor
- cancellation: wanting to cancel a subscription or service
- unknown: cannot determine intent

Customer message: "{user_message}"

Respond in this exact format:
INTENT: <intent_label>
CONFIDENCE: <0.0 to 1.0>
REASONING: <one sentence explanation>
"""

    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful customer support classifier."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        raw_output = response.choices[0].message.content.strip()
        return _parse_intent_response(raw_output)
    except openai.AuthenticationError:
        return {"intent": "unknown", "confidence": 0.0, "reasoning": "API authentication failed", "error": True}
    except openai.RateLimitError:
        return {"intent": "unknown", "confidence": 0.0, "reasoning": "Rate limit exceeded", "error": True}
    except Exception as e:
        return {"intent": "unknown", "confidence": 0.0, "reasoning": str(e), "error": True}


def _parse_intent_response(raw: str) -> dict:
    """
    Fragile regex parser for LLM output.
    Breaks if LLM changes its response format even slightly.
    """
    result = {"intent": "unknown", "confidence": 0.0, "reasoning": "Parse failed", "error": False}

    intent_match = re.search(r"INTENT:\s*(\w+)", raw, re.IGNORECASE)
    if intent_match:
        intent = intent_match.group(1).lower()
        result["intent"] = intent if intent in VALID_INTENTS else "unknown"

    confidence_match = re.search(r"CONFIDENCE:\s*([0-9.]+)", raw, re.IGNORECASE)
    if confidence_match:
        try:
            result["confidence"] = float(confidence_match.group(1))
        except ValueError:
            result["confidence"] = 0.0

    reasoning_match = re.search(r"REASONING:\s*(.+)", raw, re.IGNORECASE)
    if reasoning_match:
        result["reasoning"] = reasoning_match.group(1).strip()

    return result


# -----------------------------------------------------------------------
# SENTIMENT ANALYSIS - copy-paste of the same pattern
# -----------------------------------------------------------------------
def analyze_sentiment(user_message: str) -> dict:
    """
    Analyze the sentiment of a customer message.
    Completely separate function that duplicates the API call pattern.
    """
    # Another hardcoded prompt - same boilerplate as above
    prompt = f"""Analyze the sentiment of the following customer support message.

Customer message: "{user_message}"

Respond in this EXACT format:
SENTIMENT: <positive|neutral|negative|very_negative>
URGENCY: <low|medium|high|critical>
EMOTION: <calm|frustrated|angry|confused|satisfied>
"""

    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a sentiment analysis expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.0,
        )
        raw_output = response.choices[0].message.content.strip()
        return _parse_sentiment_response(raw_output)
    except Exception as e:
        return {"sentiment": "neutral", "urgency": "low", "emotion": "calm", "error": str(e)}


def _parse_sentiment_response(raw: str) -> dict:
    """Another fragile parser - duplicated parsing logic."""
    result = {"sentiment": "neutral", "urgency": "low", "emotion": "calm", "error": None}

    sent_match = re.search(r"SENTIMENT:\s*(\w+)", raw, re.IGNORECASE)
    if sent_match:
        result["sentiment"] = sent_match.group(1).lower()

    urgency_match = re.search(r"URGENCY:\s*(\w+)", raw, re.IGNORECASE)
    if urgency_match:
        result["urgency"] = urgency_match.group(1).lower()

    emotion_match = re.search(r"EMOTION:\s*(\w+)", raw, re.IGNORECASE)
    if emotion_match:
        result["emotion"] = emotion_match.group(1).lower()

    return result


# -----------------------------------------------------------------------
# RESPONSE GENERATION - yet another hardcoded prompt
# -----------------------------------------------------------------------
def generate_response(user_message: str, intent: str, sentiment: str) -> str:
    """
    Generate a customer support response.
    Another copy-paste of the same API call boilerplate.
    """
    # Hardcoded prompt #3 - can't change without redeployment
    prompt = f"""You are a helpful customer support agent.

Customer message: "{user_message}"
Detected intent: {intent}
Customer sentiment: {sentiment}

Generate a professional, empathetic response that:
1. Acknowledges the customer's concern
2. Addresses their specific {intent} issue
3. Provides next steps or a solution
4. Keeps the tone appropriate for a {sentiment} customer

Response:"""

    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a professional customer support agent. Be concise and helpful."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"I apologize, but I'm unable to process your request at this time. Error: {str(e)}"


# -----------------------------------------------------------------------
# BILLING SPECIFIC HANDLER - duplicated pattern again
# -----------------------------------------------------------------------
def handle_billing_query(user_message: str) -> dict:
    """
    Specialized handler for billing queries.
    Same pattern as above, slightly different hardcoded prompt.
    """
    prompt = f"""You are a billing specialist for a SaaS company.

Customer billing question: "{user_message}"

Extract the following information:
ISSUE_TYPE: <charge_dispute|refund_request|invoice_question|payment_method|subscription_change|other>
AMOUNT_MENTIONED: <dollar amount or 'none'>
URGENCY: <low|medium|high>
RECOMMENDED_ACTION: <one sentence describing what support agent should do>
"""

    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a billing support specialist."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()

        # More fragile regex parsing
        result = {}
        for field in ["ISSUE_TYPE", "AMOUNT_MENTIONED", "URGENCY", "RECOMMENDED_ACTION"]:
            match = re.search(rf"{field}:\s*(.+)", raw, re.IGNORECASE)
            result[field.lower()] = match.group(1).strip() if match else "unknown"
        return result
    except Exception as e:
        return {"issue_type": "unknown", "amount_mentioned": "none", "urgency": "medium",
                "recommended_action": "Manual review required", "error": str(e)}


# -----------------------------------------------------------------------
# TECHNICAL SUPPORT HANDLER - same pattern, 4th time
# -----------------------------------------------------------------------
def handle_technical_query(user_message: str) -> dict:
    """
    Specialized handler for technical support queries.
    Exact same boilerplate as handle_billing_query.
    """
    prompt = f"""You are a technical support specialist.

Customer technical issue: "{user_message}"

Analyze the issue and provide:
CATEGORY: <connectivity|performance|data_loss|authentication|integration|feature_bug|other>
SEVERITY: <low|medium|high|critical>
SELF_SERVICE_POSSIBLE: <yes|no>
SUGGESTED_KB_ARTICLE: <article title or 'none'>
ESCALATE_TO_ENGINEERING: <yes|no>
"""

    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a technical support specialist."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()

        result = {}
        for field in ["CATEGORY", "SEVERITY", "SELF_SERVICE_POSSIBLE", "SUGGESTED_KB_ARTICLE", "ESCALATE_TO_ENGINEERING"]:
            match = re.search(rf"{field}:\s*(.+)", raw, re.IGNORECASE)
            result[field.lower()] = match.group(1).strip() if match else "unknown"
        return result
    except Exception as e:
        return {"category": "unknown", "severity": "medium", "self_service_possible": "no",
                "suggested_kb_article": "none", "escalate_to_engineering": "no", "error": str(e)}


# -----------------------------------------------------------------------
# ESCALATION DETECTOR - same problem, 5th variation
# -----------------------------------------------------------------------
def should_escalate(user_message: str, intent: str, sentiment: str, confidence: float) -> bool:
    """
    Determine if this ticket should be escalated to a human agent.
    Uses yet another hardcoded prompt with the same boilerplate.
    """
    # Hardcoded business rules mixed with LLM call
    if confidence < LOW_CONFIDENCE:
        return True
    if sentiment in ["very_negative"] or intent == "escalation":
        return True

    prompt = f"""Determine if this customer support message requires immediate escalation to a senior human agent.

Message: "{user_message}"
Current intent: {intent}
Current sentiment: {sentiment}

Consider escalating if:
- Customer is extremely frustrated or threatening
- Issue involves potential legal action
- Data breach or security concern
- High-value customer at risk of churn
- Complex technical issue beyond tier-1 support

ESCALATE: <yes|no>
REASON: <brief explanation>
"""

    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a support escalation specialist."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()
        escalate_match = re.search(r"ESCALATE:\s*(yes|no)", raw, re.IGNORECASE)
        if escalate_match:
            return escalate_match.group(1).lower() == "yes"
        return False
    except Exception:
        return True  # Default to escalation on error


# -----------------------------------------------------------------------
# MAIN PIPELINE - orchestrates the above functions
# -----------------------------------------------------------------------
def process_customer_message(user_message: str) -> dict:
    """
    Full pipeline: classify intent -> analyze sentiment -> generate response.
    No abstraction, no LCEL chains, no reusability.
    """
    print(f"[INFO] Processing message: {user_message[:60]}...")

    # Step 1: Classify intent
    intent_result = classify_intent(user_message)
    intent = intent_result.get("intent", "unknown")
    confidence = intent_result.get("confidence", 0.0)

    # Step 2: Analyze sentiment
    sentiment_result = analyze_sentiment(user_message)
    sentiment = sentiment_result.get("sentiment", "neutral")

    # Step 3: Handle by intent type (no polymorphism, just if/else)
    specialized_data = {}
    if intent == "billing":
        specialized_data = handle_billing_query(user_message)
    elif intent == "technical_support":
        specialized_data = handle_technical_query(user_message)

    # Step 4: Check escalation
    escalate = should_escalate(user_message, intent, sentiment, confidence)

    # Step 5: Generate response
    response_text = generate_response(user_message, intent, sentiment)

    return {
        "original_message": user_message,
        "intent": intent,
        "confidence": confidence,
        "reasoning": intent_result.get("reasoning", ""),
        "sentiment": sentiment,
        "urgency": sentiment_result.get("urgency", "low"),
        "emotion": sentiment_result.get("emotion", "calm"),
        "specialized_data": specialized_data,
        "should_escalate": escalate,
        "response": response_text,
    }


# -----------------------------------------------------------------------
# BATCH PROCESSING - no parallel execution, purely sequential
# -----------------------------------------------------------------------
def process_batch(messages: list) -> list:
    """
    Process a batch of customer messages sequentially.
    No parallelism, no streaming, no optimization.
    """
    results = []
    for i, message in enumerate(messages):
        print(f"[INFO] Processing message {i+1}/{len(messages)}")
        result = process_customer_message(message)
        results.append(result)
    return results


# -----------------------------------------------------------------------
# REPORT GENERATION - hardcoded format string
# -----------------------------------------------------------------------
def generate_report(results: list) -> str:
    """Generate a plain text summary report from batch results."""
    if not results:
        return "No results to report."

    total = len(results)
    escalated = sum(1 for r in results if r.get("should_escalate"))
    intent_counts = {}
    sentiment_counts = {}

    for r in results:
        intent = r.get("intent", "unknown")
        sentiment = r.get("sentiment", "neutral")
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

    # Hardcoded report format
    report = f"""
=== CUSTOMER SUPPORT BATCH REPORT ===
Total messages processed: {total}
Escalated to human agents: {escalated} ({escalated/total*100:.1f}%)

Intent Distribution:
"""
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        report += f"  {intent}: {count} ({count/total*100:.1f}%)\n"

    report += "\nSentiment Distribution:\n"
    for sentiment, count in sorted(sentiment_counts.items(), key=lambda x: -x[1]):
        report += f"  {sentiment}: {count} ({count/total*100:.1f}%)\n"

    return report


# -----------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------
if __name__ == "__main__":
    test_messages = [
        "I was charged twice for my subscription this month!",
        "The app keeps crashing whenever I try to upload a file.",
        "How do I reset my password?",
        "I want to cancel my account immediately.",
        "I've been waiting for 3 days and nobody has helped me. This is ridiculous!",
        "Can you tell me about your enterprise pricing?",
        "I need to speak with a manager right now.",
    ]

    print("Starting legacy intent classifier pipeline...\n")
    results = process_batch(test_messages)
    report = generate_report(results)
    print(report)

    # Save results to JSON
    with open("legacy_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to legacy_results.json")
