"""Configuration and settings for the Shield Orchestrator."""

import os
from dotenv import load_dotenv

load_dotenv()


# Model pool for failover rotation — ordered by preference.
# Sticking to models confirmed to support Tool Calling.
DEFAULT_MODEL_POOL: list[str] = [
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-pro-latest",
]

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def get_gemini_api_key() -> str | None:
    """Return the Gemini API key from environment."""
    return os.getenv("GEMINI_API_KEY")


def get_agent_path() -> str:
    """Return the path to the shield-agent-mcp project."""
    return os.getenv("SHIELD_AGENT_PATH", "../shield-agent-mcp")
