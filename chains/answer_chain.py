"""
Answer Synthesis Chain
Converts SQL results into natural language explanations.
"""

import json
import logging
from typing import List, Tuple, Any, Optional

from langchain_core.prompts import PromptTemplate

from chains.llm_factory import create_llm, extract_text
from prompts.answer_synthesis import ANSWER_SYNTHESIS_TEMPLATE, ANSWER_WITH_ERROR_TEMPLATE

logger = logging.getLogger(__name__)


class AnswerChain:
    """Synthesizes natural language answers from SQL results."""
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the answer synthesis chain."""
        self.llm = create_llm(model_name, temperature=0.3)
        
        self.prompt = PromptTemplate(
            input_variables=["question", "results"],
            template=ANSWER_SYNTHESIS_TEMPLATE
        )
        
        self.error_prompt = PromptTemplate(
            input_variables=["question", "error"],
            template=ANSWER_WITH_ERROR_TEMPLATE
        )
        
        self.chain = self.prompt | self.llm
        self.error_chain = self.error_prompt | self.llm
    
    def _format_results(self, columns: List[str], rows: List[Tuple[Any, ...]]) -> str:
        """Format query results as readable text."""
        if not rows:
            return "No results returned."
        
        # Create a simple table representation
        lines = []
        
        # Header
        lines.append(" | ".join(columns))
        lines.append("-" * len(lines[0]))
        
        # Rows (limit display for prompt)
        for row in rows[:20]:  # Limit to 20 rows for the prompt
            formatted_row = []
            for val in row:
                if val is None:
                    formatted_row.append("NULL")
                elif isinstance(val, float):
                    formatted_row.append(f"{val:,.2f}")
                else:
                    formatted_row.append(str(val))
            lines.append(" | ".join(formatted_row))
        
        if len(rows) > 20:
            lines.append(f"... and {len(rows) - 20} more rows")
        
        return "\n".join(lines)
    
    def synthesize(
        self, 
        question: str, 
        sql: str,
        columns: List[str], 
        rows: List[Tuple[Any, ...]]
    ) -> dict:
        """
        Generate a natural language answer from query results.
        
        Returns:
            dict with keys: answer_text, has_table
        """
        try:
            results_text = self._format_results(columns, rows)
            
            response = self.chain.invoke({
                "question": question,
                "results": results_text
            })
            
            # Clean up the response - remove any JSON artifacts
            answer = extract_text(response).strip()
            
            # Remove markdown code blocks if present
            if answer.startswith("```"):
                lines = answer.split('\n')
                answer = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
            
            # Try to extract answer_text if model still outputs JSON
            if answer.startswith("{") and "answer_text" in answer:
                try:
                    parsed = json.loads(answer)
                    answer = parsed.get("answer_text", answer)
                except json.JSONDecodeError:
                    # Try to extract just the answer_text value
                    import re
                    match = re.search(r'"answer_text"\s*:\s*"([^"]+)"', answer)
                    if match:
                        answer = match.group(1)
            
            # Clean up any remaining artifacts
            answer = answer.strip('"').strip()
            
            # Determine if we should show a table (more than 1 row or multiple columns)
            has_table = len(rows) > 1 or (len(rows) == 1 and len(columns) > 2)
            
            logger.info(f"Answer synthesized: {answer[:100]}...")
            return {"answer_text": answer, "has_table": has_table}
            
        except Exception as e:
            logger.error(f"Answer synthesis error: {e}")
            return {
                "answer_text": f"I found the results but had trouble formatting the answer. Here's what the query returned: {len(rows)} rows of data.",
                "has_table": True
            }
    
    def synthesize_error(self, question: str, error: str) -> str:
        """Generate a helpful response for query errors."""
        try:
            response = self.error_chain.invoke({
                "question": question,
                "error": error
            })
            return extract_text(response).strip()
        except Exception as e:
            logger.error(f"Error synthesis error: {e}")
            return f"I encountered an error processing your question: {error}. Please try rephrasing your question."
