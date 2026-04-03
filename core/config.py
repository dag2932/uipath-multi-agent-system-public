import os
from dotenv import load_dotenv

load_dotenv()

# Model configuration - read from environment, updated at runtime
def get_model():
    return os.getenv("LLM_MODEL", "gpt-4o-mini")

def get_api_key():
    return os.getenv("OPENAI_API_KEY", "")


def is_llm_first() -> bool:
    """LLM-first mode is enabled by default; set LLM_FIRST=false to disable."""
    return os.getenv("LLM_FIRST", "true").strip().lower() in {"1", "true", "yes", "y", "on"}


def is_llm_required() -> bool:
    """When enabled, run should fail fast if LLM is unavailable."""
    return os.getenv("LLM_REQUIRED", "false").strip().lower() in {"1", "true", "yes", "y", "on"}

# Backwards compatibility
DEFAULT_MODEL = get_model()
OPENAI_API_KEY = get_api_key()