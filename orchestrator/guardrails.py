"""
Safety Guardrails
Hard enforcement of safety rules for SQL execution.
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class Guardrails:
    """Enforces safety rules for SQL queries."""
    
    # Patterns that are absolutely forbidden
    FORBIDDEN_PATTERNS = [
        (r'\bINSERT\s+INTO\b', "INSERT statements are not allowed"),
        (r'\bUPDATE\s+\w+\s+SET\b', "UPDATE statements are not allowed"),
        (r'\bDELETE\s+FROM\b', "DELETE statements are not allowed"),
        (r'\bDROP\s+(TABLE|DATABASE|INDEX)\b', "DROP statements are not allowed"),
        (r'\bCREATE\s+(TABLE|DATABASE|INDEX)\b', "CREATE statements are not allowed"),
        (r'\bALTER\s+TABLE\b', "ALTER statements are not allowed"),
        (r'\bTRUNCATE\s+TABLE\b', "TRUNCATE statements are not allowed"),
        (r'\bGRANT\b', "GRANT statements are not allowed"),
        (r'\bREVOKE\b', "REVOKE statements are not allowed"),
        (r'\bATTACH\s+DATABASE\b', "ATTACH DATABASE is not allowed"),
        (r'\bDETACH\s+DATABASE\b', "DETACH DATABASE is not allowed"),
        (r';\s*SELECT', "Multiple statements are not allowed"),
        (r'UNION\s+ALL\s+SELECT.*FROM\s+sqlite_', "Access to system tables is not allowed"),
    ]
    
    # Maximum query length (characters)
    MAX_QUERY_LENGTH = 2000
    
    # Maximum results
    MAX_ROWS = 1000
    
    # Query timeout in seconds
    QUERY_TIMEOUT = 5
    
    @classmethod
    def validate_query(cls, sql: str) -> Tuple[bool, str]:
        """
        Validate a SQL query for safety.
        
        Args:
            sql: The SQL query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Empty query"
        
        sql_upper = sql.upper().strip()
        
        # Must start with SELECT
        if not sql_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed"
        
        # Check query length
        if len(sql) > cls.MAX_QUERY_LENGTH:
            return False, f"Query too long (max {cls.MAX_QUERY_LENGTH} characters)"
        
        # Check forbidden patterns
        for pattern, message in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, sql_upper):
                logger.warning(f"Blocked query with pattern '{pattern}': {sql[:100]}...")
                return False, message
        
        # Check for suspicious comment patterns (SQL injection)
        if '--' in sql or '/*' in sql:
            return False, "SQL comments are not allowed"
        
        # Check for multiple statements
        # Remove string literals first to avoid false positives
        sql_no_strings = re.sub(r"'[^']*'", "", sql)
        sql_no_strings = re.sub(r'"[^"]*"', "", sql_no_strings)
        if sql_no_strings.count(';') > 1:
            return False, "Multiple SQL statements are not allowed"
        
        return True, ""
    
    @classmethod
    def ensure_limit(cls, sql: str, max_rows: int = None) -> str:
        """
        Ensure a SQL query has a LIMIT clause.
        
        Args:
            sql: The SQL query
            max_rows: Maximum rows (defaults to MAX_ROWS)
            
        Returns:
            SQL query with LIMIT clause
        """
        if max_rows is None:
            max_rows = cls.MAX_ROWS
        
        sql_upper = sql.upper()
        
        if 'LIMIT' not in sql_upper:
            # Remove trailing semicolon
            sql = sql.rstrip(';').strip()
            sql = f"{sql} LIMIT {max_rows}"
        else:
            # Check if existing limit is too high
            limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
            if limit_match:
                existing_limit = int(limit_match.group(1))
                if existing_limit > max_rows:
                    # Replace with our limit
                    sql = re.sub(
                        r'LIMIT\s+\d+', 
                        f'LIMIT {max_rows}', 
                        sql, 
                        flags=re.IGNORECASE
                    )
        
        return sql
    
    @classmethod
    def sanitize_input(cls, text: str) -> str:
        """
        Basic input sanitization.
        
        Args:
            text: User input text
            
        Returns:
            Sanitized text
        """
        # Remove potential SQL injection patterns from user input
        # This is a basic measure - the main protection is the LLM + validation
        sanitized = text.strip()
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Limit length
        if len(sanitized) > 500:
            sanitized = sanitized[:500]
        
        return sanitized
