import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scanner.db')

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds basic data."""
    logger.info(f"Initializing database at {DB_PATH}")
    conn = get_connection()
    cursor = conn.cursor()

    # Create Stocks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT
        )
    ''')

    # Create Daily Prices table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            FOREIGN KEY (stock_id) REFERENCES stocks(id),
            UNIQUE(stock_id, date)
        )
    ''')

    # Seed with NIFTY 50 (Subset for initial testing)
    nifty_50_symbols = [
        ('RELIANCE', 'Reliance Industries Ltd.'),
        ('TCS', 'Tata Consultancy Services Ltd.'),
        ('HDFCBANK', 'HDFC Bank Ltd.'),
        ('INFY', 'Infosys Ltd.'),
        ('ICICIBANK', 'ICICI Bank Ltd.'),
        ('HUL', 'Hindustan Unilever Ltd.'),
        ('ITC', 'ITC Ltd.'),
        ('SBIN', 'State Bank of India'),
        ('BHARTIARTL', 'Bharti Airtel Ltd.'),
        ('BAJFINANCE', 'Bajaj Finance Ltd.')
    ]

    cursor.executemany('''
        INSERT OR IGNORE INTO stocks (symbol, company_name)
        VALUES (?, ?)
    ''', nifty_50_symbols)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
