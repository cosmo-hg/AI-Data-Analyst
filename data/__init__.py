"""
Data module for AI Data Analyst.
Handles data loading, schema detection, and database management.
"""

from data.data_loader import DataLoader, load_uploaded_file

__all__ = [
    "DataLoader",
    "load_uploaded_file"
]
