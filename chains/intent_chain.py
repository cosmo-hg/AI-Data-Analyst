"""
Intent Classification Chain
Uses LangChain to classify user queries.
"""

import json
import logging
from typing import Optional
from langchain_core.prompts import PromptTemplate

from chains.llm_factory import create_llm, extract_text
from prompts.intent_classification import (
    INTENT_CLASSIFICATION_TEMPLATE, 
    INTENT_CLASSIFICATION_WITH_HISTORY_TEMPLATE,
    DEFAULT_SCHEMA
)

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classifies user queries as structured (SQL-answerable) or unsupported."""
    
    def __init__(self, model_name: str = "gemini-2.5-flash", custom_schema: Optional[str] = None):
        """
        Initialize the intent classifier with specified model.
        
        Args:
            model_name: Gemini model to use
            custom_schema: Custom schema description (uses default if not specified)
        """
        self.llm = create_llm(model_name, temperature=0)
        self.schema_description = custom_schema if custom_schema else DEFAULT_SCHEMA
        
        self.prompt = PromptTemplate(
            input_variables=["question", "schema_description"],
            template=INTENT_CLASSIFICATION_TEMPLATE
        )
        
        self.prompt_with_history = PromptTemplate(
            input_variables=["question", "chat_history", "schema_description"],
            template=INTENT_CLASSIFICATION_WITH_HISTORY_TEMPLATE
        )
        
        self.chain = self.prompt | self.llm
        self.chain_with_history = self.prompt_with_history | self.llm
    
    def classify(self, question: str, chat_history: Optional[str] = None) -> dict:
        """
        Classify a user question.
        
        Args:
            question: The user's question
            chat_history: Optional conversation history for context
        
        Returns:
            dict with keys: intent, confidence, reason
        """
        try:
            # Use history-aware prompt if we have context
            if chat_history:
                response = self.chain_with_history.invoke({
                    "question": question,
                    "chat_history": chat_history,
                    "schema_description": self.schema_description
                })
            else:
                response = self.chain.invoke({
                    "question": question,
                    "schema_description": self.schema_description
                })
            
            # Parse JSON response
            # Clean up response - sometimes LLM adds extra text
            response = extract_text(response).strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            result = json.loads(response)
            
            # Validate response structure
            if "intent" not in result:
                result["intent"] = "structured"  # Default to trying SQL
            if "confidence" not in result:
                result["confidence"] = 0.8
            if "reason" not in result:
                result["reason"] = "Classification completed"
                
            logger.info(f"Intent classification: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse intent response: {e}")
            # Default to structured if we can't parse
            return {
                "intent": "structured",
                "confidence": 0.5,
                "reason": "Failed to parse classification, defaulting to structured"
            }
        except Exception as e:
            logger.error(f"Intent classification error: {e}")
            return {
                "intent": "structured",
                "confidence": 0.5,
                "reason": f"Classification error: {str(e)}"
            }
