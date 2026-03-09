"""
SQL Generation and Execution Chain
Generates SQL from natural language and executes it safely.
"""

import re
import logging
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, List, Any

import yaml
from langchain_core.prompts import PromptTemplate

from chains.llm_factory import create_llm, extract_text
from prompts.sql_generation import SQL_GENERATION_TEMPLATE, SQL_GENERATION_WITH_MEMORY_TEMPLATE

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_FILE = DATA_DIR / "retail.db"
SCHEMA_FILE = DATA_DIR / "schema_description.yaml"


class SQLChain:
    """Generates and executes SQL queries from natural language."""
    
    # Dangerous SQL patterns to block
    DANGEROUS_PATTERNS = [
        r'\bINSERT\b',
        r'\bUPDATE\b',
        r'\bDELETE\b',
        r'\bDROP\b',
        r'\bCREATE\b',
        r'\bALTER\b',
        r'\bTRUNCATE\b',
        r'\bGRANT\b',
        r'\bREVOKE\b',
        r';.*SELECT',  # Multiple statements
    ]
    
    def __init__(
        self, 
        model_name: str = "gemini-2.5-flash", 
        max_rows: int = 1000, 
        timeout: int = 5,
        db_path: Optional[str] = None,
        custom_schema: Optional[str] = None
    ):
        """
        Initialize the SQL chain.
        
        Args:
            model_name: Gemini model to use
            max_rows: Maximum rows to return
            timeout: Query timeout in seconds
            db_path: Custom database path (uses default retail.db if not specified)
            custom_schema: Custom schema description (loads from YAML if not specified)
        """
        self.model_name = model_name
        self.max_rows = max_rows
        self.timeout = timeout
        
        # Use custom db path or default
        self.db_path = db_path if db_path else str(DB_FILE)
        
        # Use LLM factory for Gemini model creation
        self.llm = create_llm(model_name, temperature=0)
        
        # Use custom schema or load from file
        if custom_schema:
            self.schema_description = custom_schema
        else:
            self.schema_description = self._load_schema()
        
        self.prompt = PromptTemplate(
            input_variables=["question", "schema_description", "context"],
            template=SQL_GENERATION_TEMPLATE
        )
        
        self.prompt_with_memory = PromptTemplate(
            input_variables=["question", "chat_history", "schema_description"],
            template=SQL_GENERATION_WITH_MEMORY_TEMPLATE
        )
        
        self.chain = self.prompt | self.llm
        self.chain_with_memory = self.prompt_with_memory | self.llm
    
    def _load_schema(self) -> str:
        """Load and format schema description from YAML file if available."""
        try:
            if not SCHEMA_FILE.exists():
                return "No schema file found. Please upload a data file to analyze."
                
            with open(SCHEMA_FILE, 'r') as f:
                schema = yaml.safe_load(f)
            
            if not schema:
                return "Schema file is empty. Please upload a data file to analyze."
            
            # Format as readable text - handle any table structure
            lines = []
            
            for table_name, table_info in schema.items():
                lines.append(f"Table: {table_name}")
                
                if isinstance(table_info, dict):
                    if 'description' in table_info:
                        lines.append(f"Description: {table_info.get('description', 'N/A')}")
                    
                    lines.append("\nColumns:")
                    for col, info in table_info.get('columns', {}).items():
                        desc = info.get('description', info) if isinstance(info, dict) else info
                        lines.append(f"  - {col}: {desc}")
                    
                    if 'derived_metrics' in table_info:
                        lines.append("\nDerived Metrics:")
                        for metric, info in table_info.get('derived_metrics', {}).items():
                            if isinstance(info, dict):
                                lines.append(f"  - {metric}: {info.get('formula', '')} ({info.get('description', '')})")
                            else:
                                lines.append(f"  - {metric}: {info}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            return "No schema available. Please upload a data file to analyze."
    
    def _validate_sql(self, sql: str) -> Tuple[bool, str]:
        """
        Validate SQL for safety.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        sql_upper = sql.upper()
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, sql_upper):
                return False, f"Blocked: SQL contains forbidden pattern '{pattern}'"
        
        # Must be a SELECT statement
        if not sql_upper.strip().startswith('SELECT'):
            return False, "Blocked: Only SELECT statements are allowed"
        
        # Check for multiple statements
        if sql.count(';') > 1:
            return False, "Blocked: Multiple SQL statements detected"
        
        return True, ""
    
    def _ensure_limit(self, sql: str) -> str:
        """Ensure SQL has a LIMIT clause."""
        sql_upper = sql.upper()
        
        if 'LIMIT' not in sql_upper:
            # Remove trailing semicolon if present
            sql = sql.rstrip(';').strip()
            sql = f"{sql} LIMIT {self.max_rows}"
        
        return sql
    
    def _clean_sql(self, sql: str) -> str:
        """Clean up generated SQL - handle garbled LLM output."""
        # Remove markdown code blocks if present
        sql = sql.strip()
        if sql.startswith("```"):
            lines = sql.split('\n')
            sql = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
        if sql.startswith("sql"):
            sql = sql[3:].strip()
        
        # If there are multiple statements separated by semicolons, keep only the first
        if ';' in sql:
            statements = sql.split(';')
            # Find the first statement that starts with SELECT
            for stmt in statements:
                stmt = stmt.strip()
                if stmt.upper().startswith('SELECT'):
                    sql = stmt
                    break
            else:
                sql = statements[0].strip()
        
        # The model sometimes outputs examples from the prompt - truncate at first "Question:"
        if 'Question:' in sql:
            sql = sql.split('Question:')[0]
        
        # Also truncate at common signs of prompt leakage (but be careful with multi-line SQL)
        for marker in ['Respond with', 'Now generate', 'CRITICAL RULES', 'INSTRUCTIONS:', 'Example', 'Human:', 'Assistant:']:
            if marker in sql:
                sql = sql.split(marker)[0]
        
        # Remove SQL comments (-- style)
        lines = sql.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove inline comments
            if '--' in line:
                line = line.split('--')[0]
            line = line.strip()
            if line:  # Only keep non-empty lines
                cleaned_lines.append(line)
        sql = ' '.join(cleaned_lines)
        
        # If there are still multiple complete SELECT statements, only keep the first one
        # Check for pattern like "LIMIT N SELECT" which indicates a new query
        if sql.upper().count('SELECT') > 1:
            match = re.search(r'LIMIT\s+\d+\s+SELECT', sql.upper())
            if match:
                sql = sql[:match.start() + sql.upper()[match.start():].find('SELECT') - 1].strip()
        
        # Remove trailing semicolons for consistency
        sql = sql.rstrip(';').strip()
        
        return sql
    
    def generate_sql(self, question: str, chat_history: Optional[str] = None) -> str:
        """Generate SQL from a natural language question."""
        try:
            if chat_history:
                response = self.chain_with_memory.invoke({
                    "question": question,
                    "chat_history": chat_history,
                    "schema_description": self.schema_description
                })
            else:
                response = self.chain.invoke({
                    "question": question,
                    "schema_description": self.schema_description,
                    "context": ""
                })
            
            sql = self._clean_sql(extract_text(response))
            logger.info(f"Generated SQL: {sql}")
            
            return sql
            
        except Exception as e:
            logger.error(f"SQL generation error: {e}")
            raise
    
    def execute_sql(self, sql: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
        """
        Execute SQL query safely.
        
        Returns:
            Tuple of (column_names, rows)
        """
        # Validate first
        is_valid, error = self._validate_sql(sql)
        if not is_valid:
            raise ValueError(error)
        
        # Ensure LIMIT
        sql = self._ensure_limit(sql)
        
        # Execute with timeout using read-only connection
        try:
            # Open in read-only mode
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=self.timeout)
            cursor = conn.cursor()
            
            cursor.execute(sql)
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            # Fetch results
            rows = cursor.fetchall()
            
            conn.close()
            
            logger.info(f"Query returned {len(rows)} rows")
            return columns, rows
            
        except sqlite3.Error as e:
            logger.error(f"SQL execution error: {e}")
            raise ValueError(f"Database error: {str(e)}")
    
    def run(self, question: str, chat_history: Optional[str] = None) -> dict:
        """
        Full pipeline: generate SQL, validate, execute, return results.
        
        Returns:
            dict with keys: sql, columns, rows, error
        """
        result = {
            "sql": None,
            "columns": [],
            "rows": [],
            "error": None
        }
        
        try:
            # Generate SQL
            sql = self.generate_sql(question, chat_history)
            result["sql"] = sql
            
            # Execute
            columns, rows = self.execute_sql(sql)
            result["columns"] = columns
            result["rows"] = rows
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"SQL chain error: {e}")
        
        return result
