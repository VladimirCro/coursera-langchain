"""
Refactored Intent Classifier - LangChain Implementation
========================================================
This module refactors the legacy monolithic intent_classifier.py using:

1. PromptTemplate / ChatPromptTemplate  - externalized, reusable prompt management
2. ChatOpenAI / ChatAnthropic           - provider-agnostic LLM wrappers
3. PydanticOutputParser                 - structured, validated output parsing
4. LCEL (LangChain Expression Language) - composable pipeline chains (|)
5. External configuration               - prompts.yaml + config.json, no hardcoding

Key improvements over legacy version:
- Prompts live in config/prompts.yaml  → change without code redeployment
- Structured Pydantic models           → validated output, no fragile regex
- LCEL chains                          → readable, composable pipelines
- Single LLM wrapper abstraction       → swap providers by changing .env
- DRY code                             → no copy-paste boilerplate
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Literal, Optional

import yaml
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Bootstrap: load environment variables
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", Path(__file__).parent.parent / "config"))


def load_config() -> dict:
    """Load JSON configuration from config/config.json."""
    config_path = CONFIG_DIR / "config.json"
    with open(config_path) as f:
        return json.load(f)


def load_prompts() -> dict:
    """Load prompt templates from config/prompts.yaml."""
    prompts_path = CONFIG_DIR / "prompts.yaml"
    with open(prompts_path) as f:
        return yaml.safe_load(f)


CFG = load_config()
PROMPTS = load_prompts()

# ---------------------------------------------------------------------------
# Pydantic output models (replace fragile regex parsing)
# ---------------------------------------------------------------------------

IntentLabel = Literal[
    "billing",
    "technical_support",
    "account_management",
    "general_inquiry",
    "complaint",
    "escalation",
    "cancellation",
    "unknown",
]

SentimentLabel = Literal["positive", "neutral", "negative", "very_negative"]
UrgencyLabel = Literal["low", "medium", "high", "critical"]
VALID_EMOTIONS = {"calm", "frustrated", "angry", "confused", "satisfied"}


class IntentClassification(BaseModel):
    """Structured output for intent classification."""

    intent: IntentLabel = Field(description="The classified intent of the customer message")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)
    reasoning: str = Field(description="One-sentence explanation of the classification")

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)


class SentimentAnalysis(BaseModel):
    """Structured output for sentiment analysis."""

    sentiment: SentimentLabel = Field(description="Overall sentiment of the message")
    urgency: UrgencyLabel = Field(description="Urgency level of the customer's issue")
    emotion: str = Field(description="Primary detected emotion")

    @field_validator("emotion")
    @classmethod
    def normalize_emotion(cls, v: str) -> str:
        """Map any LLM-returned emotion to the closest valid label."""
        v = v.lower().strip()
        if v in VALID_EMOTIONS:
            return v
        # Simple proximity mapping for common LLM deviations
        mapping = {
            "curious": "calm",
            "happy": "satisfied",
            "sad": "frustrated",
            "irritated": "frustrated",
            "annoyed": "frustrated",
            "upset": "angry",
            "anxious": "confused",
            "worried": "confused",
            "neutral": "calm",
        }
        return mapping.get(v, "calm")


class EscalationDecision(BaseModel):
    """Structured output for escalation check."""

    should_escalate: bool = Field(description="Whether the ticket should be escalated to a human agent")
    reason: str = Field(description="Brief explanation for the escalation decision")


# ---------------------------------------------------------------------------
# LLM factory - single place to configure the model
# ---------------------------------------------------------------------------

def build_llm(temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> ChatOpenAI:
    """
    Build and return a configured LLM instance.
    Provider and model are read from environment + config.json.
    Swap providers by changing LLM_PROVIDER in .env.
    """
    model_cfg = CFG["model"]
    provider = os.getenv("LLM_PROVIDER", model_cfg.get("provider", "openai"))
    model_name = os.getenv("LLM_MODEL_NAME", model_cfg["name"])
    temp = temperature if temperature is not None else model_cfg["temperature"]
    tokens = max_tokens if max_tokens is not None else model_cfg["max_tokens"]

    if provider == "anthropic":
        # Lazy import - only required if using Anthropic
        from langchain_anthropic import ChatAnthropic  # type: ignore
        return ChatAnthropic(model=model_name, temperature=temp, max_tokens=tokens)

    return ChatOpenAI(model=model_name, temperature=temp, max_tokens=tokens)


# ---------------------------------------------------------------------------
# Chain builders using LCEL (prompt | llm.with_structured_output)
# with_structured_output uses OpenAI function calling - far more reliable
# than PydanticOutputParser + format_instructions for structured data.
# ---------------------------------------------------------------------------

def _build_structured_chain(pydantic_model, prompt_key: str, temperature: float = 0.0):
    """
    Generic builder: creates a prompt | llm.with_structured_output(model) chain.
    Uses function_calling method explicitly for broad model compatibility.
    """
    prompt_cfg = PROMPTS[prompt_key]
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_cfg["system_message"].strip()),
        ("human", prompt_cfg["human_template"].strip()),
    ])
    llm = build_llm(temperature=temperature)
    return prompt | llm.with_structured_output(pydantic_model, method="function_calling")


def build_intent_chain():
    """LCEL chain: prompt | llm.with_structured_output -> IntentClassification"""
    return _build_structured_chain(IntentClassification, "intent_classification")


def build_sentiment_chain():
    """LCEL chain: prompt | llm.with_structured_output -> SentimentAnalysis"""
    return _build_structured_chain(SentimentAnalysis, "sentiment_analysis")


def build_escalation_chain():
    """LCEL chain: prompt | llm.with_structured_output -> EscalationDecision"""
    return _build_structured_chain(EscalationDecision, "escalation_check")


def build_response_chain():
    """LCEL chain: prompt | llm -> AIMessage (free-text response)"""
    prompt_cfg = PROMPTS["response_generation"]
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_cfg["system_message"].strip()),
        ("human", prompt_cfg["human_template"].strip()),
    ])
    llm = build_llm(
        temperature=CFG["model"]["response_generation_temperature"],
        max_tokens=CFG["model"]["response_generation_max_tokens"],
    )
    return prompt | llm


# ---------------------------------------------------------------------------
# Main pipeline: compose all chains
# ---------------------------------------------------------------------------

class IntentClassifier:
    """
    Orchestrates the full customer support classification pipeline.

    Usage:
        classifier = IntentClassifier()
        result = classifier.process("I was charged twice this month!")
    """

    def __init__(self):
        logger.info("Initializing IntentClassifier chains...")
        self.intent_chain = build_intent_chain()
        self.sentiment_chain = build_sentiment_chain()
        self.escalation_chain = build_escalation_chain()
        self.response_chain = build_response_chain()
        self.thresholds = CFG["thresholds"]
        logger.info("IntentClassifier ready.")

    def _should_auto_escalate(
        self,
        intent: IntentLabel,
        sentiment: SentimentLabel,
        confidence: float,
    ) -> bool:
        """Apply rule-based escalation checks before calling the LLM."""
        if confidence < self.thresholds["auto_escalate_below_confidence"]:
            return True
        if intent in CFG["auto_escalate_intents"]:
            return True
        if sentiment in CFG["auto_escalate_sentiments"]:
            return True
        return False

    def process(self, user_message: str) -> dict:
        """
        Run the full pipeline for a single customer message.

        Steps:
          1. Classify intent              (LCEL chain -> IntentClassification)
          2. Analyze sentiment            (LCEL chain -> SentimentAnalysis)
          3. Check escalation             (rules + LCEL chain -> EscalationDecision)
          4. Generate support response    (LCEL chain -> str)
        """
        logger.info("Processing: %s...", user_message[:60])

        # Step 1: Intent classification
        intent_result: IntentClassification = self.intent_chain.invoke({
            "user_message": user_message,
        })
        logger.debug("Intent: %s (%.2f)", intent_result.intent, intent_result.confidence)

        # Step 2: Sentiment analysis
        sentiment_result: SentimentAnalysis = self.sentiment_chain.invoke({
            "user_message": user_message,
        })
        logger.debug("Sentiment: %s | Urgency: %s", sentiment_result.sentiment, sentiment_result.urgency)

        # Step 3: Escalation decision
        auto_escalate = self._should_auto_escalate(
            intent_result.intent,
            sentiment_result.sentiment,
            intent_result.confidence,
        )

        if auto_escalate:
            escalation = EscalationDecision(
                should_escalate=True,
                reason="Auto-escalated based on intent/sentiment/confidence rules.",
            )
        else:
            escalation: EscalationDecision = self.escalation_chain.invoke({
                "user_message": user_message,
                "intent": intent_result.intent,
                "sentiment": sentiment_result.sentiment,
                "confidence": intent_result.confidence,
            })

        # Step 4: Generate response
        ai_message = self.response_chain.invoke({
            "user_message": user_message,
            "intent": intent_result.intent,
            "sentiment": sentiment_result.sentiment,
            "urgency": sentiment_result.urgency,
        })
        response_text = ai_message.content

        return {
            "original_message": user_message,
            # Intent classification
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "reasoning": intent_result.reasoning,
            # Sentiment
            "sentiment": sentiment_result.sentiment,
            "urgency": sentiment_result.urgency,
            "emotion": sentiment_result.emotion,
            # Escalation
            "should_escalate": escalation.should_escalate,
            "escalation_reason": escalation.reason,
            # Generated response
            "response": response_text,
        }

    def process_batch(self, messages: List[str]) -> List[dict]:
        """Process a list of messages and return all results."""
        results = []
        for i, message in enumerate(messages):
            logger.info("Batch progress: %d/%d", i + 1, len(messages))
            result = self.process(message)
            results.append(result)
        return results

    @staticmethod
    def generate_report(results: List[dict]) -> str:
        """Generate a summary report from batch processing results."""
        if not results:
            return "No results to report."

        total = len(results)
        escalated = sum(1 for r in results if r.get("should_escalate"))

        intent_counts: dict = {}
        sentiment_counts: dict = {}
        for r in results:
            intent_counts[r["intent"]] = intent_counts.get(r["intent"], 0) + 1
            sentiment_counts[r["sentiment"]] = sentiment_counts.get(r["sentiment"], 0) + 1

        lines = [
            "=" * 50,
            "  CUSTOMER SUPPORT BATCH REPORT",
            "=" * 50,
            f"Total messages processed : {total}",
            f"Escalated to human agents: {escalated} ({escalated / total * 100:.1f}%)",
            "",
            "Intent Distribution:",
        ]
        for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {intent:<25} {count:>3}  ({count / total * 100:.1f}%)")

        lines += ["", "Sentiment Distribution:"]
        for sentiment, count in sorted(sentiment_counts.items(), key=lambda x: -x[1]):
            lines += [f"  {sentiment:<25} {count:>3}  ({count / total * 100:.1f}%)"]

        lines.append("=" * 50)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
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

    classifier = IntentClassifier()
    results = classifier.process_batch(test_messages)
    report = classifier.generate_report(results)
    print(report)

    output_path = Path(__file__).parent.parent / "refactored_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
