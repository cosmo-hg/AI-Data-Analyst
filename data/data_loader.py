"""
Data Loader Module
Handles loading CSV/Excel files into SQLite and generating schema descriptions.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
import pandas as pd
import tempfile
import os

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads CSV/Excel files into a SQLite database and generates schema descriptions.
    """
    
    # Type mapping from pandas to human-readable
    TYPE_MAPPING = {
        'int64': 'integer',
        'float64': 'decimal number',
        'object': 'text',
        'datetime64[ns]': 'date/time',
        'bool': 'true/false',
        'category': 'category'
    }
    
    def __init__(self):
        """Initialize the data loader."""
        self.temp_dir = tempfile.mkdtemp(prefix="ai_analyst_")
        logger.info(f"DataLoader initialized with temp dir: {self.temp_dir}")
    
    def load_file(
        self, 
        file_content: bytes, 
        filename: str,
        table_name: str = "uploaded_data"
    ) -> Tuple[str, str, Dict]:
        """
        Load a file into SQLite and return database path and schema.
        
        Args:
            file_content: Raw file contents as bytes
            filename: Original filename (used to detect format)
            table_name: Name for the table in SQLite
            
        Returns:
            Tuple of (db_path, schema_description, schema_dict)
        """
        # Determine file type and read with pandas
        filename_lower = filename.lower()
        
        try:
            if filename_lower.endswith('.csv'):
                df = pd.read_csv(
                    pd.io.common.BytesIO(file_content),
                    encoding='utf-8',
                    on_bad_lines='skip'
                )
            elif filename_lower.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(
                    pd.io.common.BytesIO(file_content),
                    engine='openpyxl'
                )
            else:
                raise ValueError(f"Unsupported file type: {filename}")
            
            logger.info(f"Loaded {len(df)} rows from {filename}")
            
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            raise ValueError(f"Failed to read file: {str(e)}")
        
        # Clean column names (remove special chars, replace spaces)
        df.columns = [self._clean_column_name(col) for col in df.columns]
        
        # Create SQLite database
        db_path = os.path.join(self.temp_dir, f"{table_name}.db")
        
        try:
            conn = sqlite3.connect(db_path)
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            conn.close()
            logger.info(f"Created SQLite database at: {db_path}")
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise ValueError(f"Failed to create database: {str(e)}")
        
        # Generate schema description
        schema_dict = self._generate_schema_dict(df, table_name)
        schema_description = self._format_schema_description(schema_dict)
        
        return db_path, schema_description, schema_dict
    
    def _clean_column_name(self, name: str) -> str:
        """Clean column name to be SQL-friendly."""
        # Convert to string if not already
        name = str(name)
        # Replace spaces and special chars with underscores
        cleaned = ''.join(c if c.isalnum() else '_' for c in name)
        # Remove consecutive underscores
        while '__' in cleaned:
            cleaned = cleaned.replace('__', '_')
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        # Ensure it doesn't start with a number
        if cleaned and cleaned[0].isdigit():
            cleaned = 'col_' + cleaned
        return cleaned or 'column'
    
    def _generate_schema_dict(self, df: pd.DataFrame, table_name: str) -> Dict:
        """Generate a schema dictionary from a DataFrame."""
        columns = {}
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            human_type = self.TYPE_MAPPING.get(dtype, 'text')
            
            # Generate description based on column content
            sample_values = df[col].dropna().head(3).tolist()
            sample_str = ", ".join(str(v)[:20] for v in sample_values)
            
            # Detect if it might be an ID column
            is_unique = df[col].nunique() == len(df)
            
            description = f"{human_type}"
            if is_unique and len(df) > 1:
                description += " (likely identifier/key)"
            if sample_str:
                description += f" - examples: {sample_str}"
            
            columns[col] = {
                "type": human_type,
                "description": description,
                "sample_values": sample_values
            }
        
        return {
            "table_name": table_name,
            "row_count": len(df),
            "columns": columns
        }
    
    def _format_schema_description(self, schema_dict: Dict) -> str:
        """Format schema dictionary as a readable string for LLM prompts."""
        lines = [
            f"Table: {schema_dict['table_name']}",
            f"Total rows: {schema_dict['row_count']:,}",
            "\nColumns:"
        ]
        
        for col_name, col_info in schema_dict['columns'].items():
            lines.append(f"  - {col_name}: {col_info['description']}")
        
        return "\n".join(lines)
    
    def cleanup(self):
        """Clean up temporary files."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temp dir: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp dir: {e}")


# Convenience function for Streamlit session
def load_uploaded_file(
    file_content: bytes,
    filename: str,
    table_name: str = "data"
) -> Tuple[str, str, Dict]:
    """
    Convenience function to load a file without managing DataLoader instance.
    
    Returns:
        Tuple of (db_path, schema_description, schema_dict)
    """
    loader = DataLoader()
    return loader.load_file(file_content, filename, table_name)
