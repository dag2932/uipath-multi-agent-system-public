import os
from dotenv import load_dotenv

load_dotenv()

# Model configuration
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")  # Default to a cost-effective model
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Optional, only needed if using LLM