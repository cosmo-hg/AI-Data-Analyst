"""
LLM Factory Module
Creates Gemini LLM instances with proper response handling.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def create_llm(model_name: str, temperature: float = 0) -> Any:
    """
    Create a Gemini LLM instance.
    
    Args:
        model_name: Name of the Gemini model
        temperature: Temperature for generation
        
    Returns:
        ChatGoogleGenerativeAI instance
    """
    from config import get_gemini_api_key
    
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is required. "
            "Get your API key from https://aistudio.google.com/apikey and add it to .env file."
        )
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        logger.info(f"Creating Gemini LLM: {model_name}")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
            convert_system_message_to_human=True
        )
    except ImportError:
        raise ImportError(
            "langchain-google-genai package is required. "
            "Install with: pip install langchain-google-genai"
        )


def extract_text(response) -> str:
    """
    Extract text content from LLM response.
    Handles AIMessage objects with string or list content.
    
    Args:
        response: LLM response (AIMessage, string, or other)
        
    Returns:
        String content
    """
    if hasattr(response, 'content'):
        content = response.content
        # Gemini 3 sometimes returns content as a list of parts
        if isinstance(content, list):
            # Extract text from each part
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif hasattr(part, 'text'):
                    text_parts.append(part.text)
                elif isinstance(part, dict) and 'text' in part:
                    text_parts.append(part['text'])
                else:
                    text_parts.append(str(part))
            return ''.join(text_parts)
        return str(content)
    return str(response)
