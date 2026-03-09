"""
SQL Generation Prompt Template
Generates SQL queries from natural language questions.
"""

SQL_GENERATION_TEMPLATE = """You are a SQL expert for a data analysis system.

DATABASE SCHEMA:
{schema_description}

CRITICAL RULES:
1. Only generate SELECT statements - no INSERT, UPDATE, DELETE, DROP, etc.
2. Always include a LIMIT clause (max 1000 rows)
3. Use the exact table and column names from the schema above
4. Use appropriate aggregations (SUM, COUNT, AVG, etc.) for summary questions
5. Handle NULL values appropriately
6. Be precise with column names - they are case-sensitive
7. DO NOT include comments (--) in your SQL
8. DO NOT use placeholders - generate complete, executable SQL

EXAMPLES:

Question: How many rows are there?
SQL: SELECT COUNT(*) as total_rows FROM data LIMIT 1

Question: Show me 5 sample records
SQL: SELECT * FROM data LIMIT 5

Question: Find a specific record
SQL: SELECT * FROM data WHERE column_name = 'value' LIMIT 10

Now generate SQL for this question:
Question: {question}

{context}

Respond with ONLY the SQL query. No explanations, no comments, no markdown, just executable SQL.
"""


SQL_GENERATION_WITH_MEMORY_TEMPLATE = """Generate a single SQL query based on the schema and conversation.

DATABASE SCHEMA:
{schema_description}

PREVIOUS CONVERSATION:
{chat_history}

CURRENT QUESTION: {question}

RULES:
- Generate ONLY ONE SELECT statement
- Use the exact table and column names from the schema
- Include LIMIT clause
- Use the conversation context to understand references like "that person", "that record", etc.

Generate SQL for the current question (one line only):
"""
