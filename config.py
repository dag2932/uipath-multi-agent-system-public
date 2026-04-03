import os
from dotenv import load_dotenv

load_dotenv()

# Model configuration - read from environment, updated at runtime
def get_model():
    return os.getenv("LLM_MODEL", "gpt-4o-mini")

def get_api_key():
    return os.getenv("OPENAI_API_KEY", "")

# Backwards compatibility
DEFAULT_MODEL = get_model()
OPENAI_API_KEY = get_api_key()