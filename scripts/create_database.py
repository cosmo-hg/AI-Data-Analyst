"""
Database Creation Script
Converts the Online Retail Excel file to a SQLite database.
"""

import pandas as pd
import sqlite3
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EXCEL_FILE = PROJECT_ROOT / "online_retail_II.xlsx"
DB_FILE = DATA_DIR / "retail.db"


def load_excel_data() -> pd.DataFrame:
    """Load and combine all sheets from the Excel file."""
    logger.info(f"Loading Excel file: {EXCEL_FILE}")
    
    # Read all sheets
    excel_file = pd.ExcelFile(EXCEL_FILE)
    sheets = excel_file.sheet_names
    logger.info(f"Found sheets: {sheets}")
    
    # Combine all sheets
    dfs = []
    for sheet in sheets:
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
        logger.info(f"Sheet '{sheet}': {len(df)} rows")
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Total rows after combining: {len(combined)}")
    
    return combined


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and preprocess the data."""
    logger.info("Cleaning data...")
    
    # Standardize column names (remove spaces, ensure consistency)
    df.columns = df.columns.str.strip().str.replace(' ', '')
    
    # Rename 'Customer ID' to 'CustomerID' if present
    if 'CustomerID' not in df.columns and 'Customer ID' in df.columns:
        df = df.rename(columns={'Customer ID': 'CustomerID'})
    
    # Log column names
    logger.info(f"Columns: {list(df.columns)}")
    
    # Remove rows where essential fields are missing
    initial_count = len(df)
    df = df.dropna(subset=['Invoice', 'StockCode', 'Quantity', 'Price'])
    logger.info(f"Removed {initial_count - len(df)} rows with missing essential fields")
    
    # Convert data types
    df['Invoice'] = df['Invoice'].astype(str)
    df['StockCode'] = df['StockCode'].astype(str)
    df['Description'] = df['Description'].fillna('').astype(str)
    df['Quantity'] = df['Quantity'].astype(int)
    df['Price'] = df['Price'].astype(float)
    df['Country'] = df['Country'].fillna('Unknown').astype(str)
    
    # Handle CustomerID - keep as nullable
    if 'CustomerID' in df.columns:
        df['CustomerID'] = df['CustomerID'].apply(lambda x: int(x) if pd.notna(x) else None)
    
    # Ensure InvoiceDate is datetime
    if 'InvoiceDate' in df.columns:
        df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    
    logger.info(f"Final row count: {len(df)}")
    
    return df


def create_database(df: pd.DataFrame) -> None:
    """Create SQLite database and populate transactions table."""
    logger.info(f"Creating database: {DB_FILE}")
    
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Remove existing database if present
    if DB_FILE.exists():
        DB_FILE.unlink()
        logger.info("Removed existing database")
    
    # Create connection and write data
    conn = sqlite3.connect(DB_FILE)
    
    # Write DataFrame to SQLite
    df.to_sql('transactions', conn, index=False, if_exists='replace')
    
    # Create indexes for common queries
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX idx_invoice ON transactions(Invoice)")
    cursor.execute("CREATE INDEX idx_stockcode ON transactions(StockCode)")
    cursor.execute("CREATE INDEX idx_customer ON transactions(CustomerID)")
    cursor.execute("CREATE INDEX idx_country ON transactions(Country)")
    cursor.execute("CREATE INDEX idx_date ON transactions(InvoiceDate)")
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM transactions")
    count = cursor.fetchone()[0]
    logger.info(f"Database created with {count} rows")
    
    # Show sample
    cursor.execute("SELECT * FROM transactions LIMIT 3")
    sample = cursor.fetchall()
    logger.info(f"Sample rows: {sample}")
    
    conn.close()
    logger.info("Database creation complete!")


def main():
    """Main execution function."""
    logger.info("Starting database creation...")
    
    # Load data
    df = load_excel_data()
    
    # Clean data
    df = clean_data(df)
    
    # Create database
    create_database(df)
    
    logger.info("Done!")


if __name__ == "__main__":
    main()
