"""
Core Orchestrator
Central controller that coordinates all chains and enforces guardrails.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from collections import deque

from chains.intent_chain import IntentClassifier
from chains.sql_chain import SQLChain
from chains.answer_chain import AnswerChain
from orchestrator.guardrails import Guardrails

# Setup logging
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configure file logging
log_file = LOGS_DIR / f"analyst_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SimpleMemory:
    """Simple conversation memory keeping last k exchanges."""
    
    def __init__(self, k: int = 2):
        self.k = k
        self.history: deque = deque(maxlen=k * 2)  # *2 for human/ai pairs
    
    def add_exchange(self, human_input: str, ai_output: str):
        """Add a human/AI exchange to memory."""
        self.history.append(("Human", human_input))
        self.history.append(("Assistant", ai_output))
    
    def get_formatted_history(self) -> str:
        """Get formatted chat history string."""
        if not self.history:
            return ""
        return "\n".join([f"{role}: {content}" for role, content in self.history])
    
    def clear(self):
        """Clear the memory."""
        self.history.clear()


class DataAnalystOrchestrator:
    """
    Central orchestrator for the AI Data Analyst.
    Coordinates intent classification, SQL generation, execution, and answer synthesis.
    """
    
    def __init__(
        self, 
        model_name: str = "gemini-2.5-flash",
        db_path: Optional[str] = None,
        custom_schema: Optional[str] = None
    ):
        """
        Initialize the orchestrator with all chains.
        
        Args:
            model_name: Name of the Gemini model to use
            db_path: Custom database path (uses default retail.db if not specified)
            custom_schema: Custom schema description for uploaded files
        """
        self.model_name = model_name
        self.db_path = db_path
        self.custom_schema = custom_schema
        
        # Initialize chains
        logger.info(f"Initializing orchestrator with model: {model_name}")
        self.intent_classifier = IntentClassifier(model_name=model_name, custom_schema=custom_schema)
        self.sql_chain = SQLChain(
            model_name=model_name,
            db_path=db_path,
            custom_schema=custom_schema
        )
        self.answer_chain = AnswerChain(model_name=model_name)
        
        # Conversation memory - keep last 2 exchanges
        self.memory = SimpleMemory(k=2)
        
        logger.info("Orchestrator initialized successfully")
    
    def _get_chat_history(self) -> str:
        """Get formatted chat history for context."""
        return self.memory.get_formatted_history()
    
    def _log_interaction(
        self, 
        question: str, 
        intent: dict,
        sql: Optional[str],
        result: dict,
        answer: str
    ) -> None:
        """Log the complete interaction for debugging."""
        logger.info("=" * 50)
        logger.info(f"Question: {question}")
        logger.info(f"Intent: {intent}")
        logger.info(f"SQL: {sql}")
        logger.info(f"Result rows: {len(result.get('rows', []))}")
        logger.info(f"Error: {result.get('error')}")
        logger.info(f"Answer: {answer[:200]}...")
        logger.info("=" * 50)
    
    def process_query(self, question: str) -> Dict[str, Any]:
        """
        Process a user query through the full pipeline.
        
        Args:
            question: User's natural language question
            
        Returns:
            dict with keys:
                - answer: Natural language answer
                - sql: The SQL query (if applicable)
                - columns: Column names from result
                - rows: Data rows from result
                - has_table: Whether to display results as table
                - error: Error message if any
                - intent: The classified intent
        """
        response = {
            "answer": "",
            "sql": None,
            "columns": [],
            "rows": [],
            "has_table": False,
            "error": None,
            "intent": None
        }
        
        try:
            # 1. Sanitize input
            question = Guardrails.sanitize_input(question)
            logger.info(f"Processing question: {question}")
            
            # 2. Get chat history for context (needed for follow-up questions)
            chat_history = self._get_chat_history()
            
            # 3. Classify intent (with context for follow-up questions)
            intent = self.intent_classifier.classify(question, chat_history)
            response["intent"] = intent
            
            if intent["intent"] == "unsupported":
                response["answer"] = (
                    f"I'm sorry, I can't answer that question with the available data. "
                    f"Reason: {intent.get('reason', 'Question not supported')}. "
                    f"Please try asking a question about the data you've uploaded."
                )
                return response
            
            # 4. Generate and execute SQL (chat_history already fetched above)
            sql_result = self.sql_chain.run(question, chat_history)
            response["sql"] = sql_result["sql"]
            
            if sql_result["error"]:
                # Handle SQL error
                response["error"] = sql_result["error"]
                response["answer"] = self.answer_chain.synthesize_error(
                    question, sql_result["error"]
                )
                return response
            
            response["columns"] = sql_result["columns"]
            response["rows"] = sql_result["rows"]
            
            # 5. Synthesize answer
            answer_result = self.answer_chain.synthesize(
                question,
                sql_result["sql"],
                sql_result["columns"],
                sql_result["rows"]
            )
            
            response["answer"] = answer_result["answer_text"]
            response["has_table"] = answer_result.get("has_table", len(sql_result["rows"]) > 1)
            
            # 6. Update memory
            self.memory.add_exchange(question, response["answer"])
            
            # 7. Log interaction
            self._log_interaction(
                question, intent, sql_result["sql"], sql_result, response["answer"]
            )
            
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            response["error"] = str(e)
            response["answer"] = (
                f"I encountered an unexpected error: {str(e)}. "
                "Please try rephrasing your question or check the logs for details."
            )
        
        return response
    
    def clear_memory(self) -> None:
        """Clear conversation memory."""
        self.memory.clear()
        logger.info("Conversation memory cleared")
    
    def get_schema_info(self) -> str:
        """Get the schema description for display."""
        return self.sql_chain.schema_description

