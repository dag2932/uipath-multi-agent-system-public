#!/usr/bin/env python3
"""Quick test to verify OpenAI API is working."""

import os
import sys
from config import get_api_key, get_model

def test_api():
    """Test OpenAI API connectivity."""
    api_key = get_api_key()
    model = get_model()
    
    print(f"Testing OpenAI API...")
    print(f"  API Key: {'✓ Set' if api_key else '✗ Not set'}")
    print(f"  Model: {model}")
    
    if not api_key:
        print("\n❌ API key not configured. Set OPENAI_API_KEY environment variable.")
        return False
    
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=0.7
        )
        
        # Simple test call
        response = llm.invoke("Say 'API is working' in exactly 3 words.")
        
        print(f"\n✅ API is working!")
        print(f"Response: {response.content}")
        return True
        
    except Exception as e:
        print(f"\n❌ API error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
