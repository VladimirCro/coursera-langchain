"""
Configuration and logging setup.
Fixes Issue #1: Hardcoded API key - now loaded from environment variables.
Fixes Issue #4: Inconsistent model usage - single model configuration.
"""

import logging
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    logger.warning("OPENAI_API_KEY not found - chain invocations will fail")


def get_model(
    model_name: str = "gpt-4-turbo",
    temperature: float = 0.3,
) -> ChatOpenAI:
    """Return a configured LLM instance. Single place to change the model."""
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_key=API_KEY,
    )
