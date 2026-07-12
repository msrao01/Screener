import pandas as pd
import logging
from src.db.database import get_connection

logger = logging.getLogger(__name__)

class IndicatorEngine:
    """
    Handles the calculation of technical indicators (EMAs, RSI, Volume)
    for the scanner, operating on data loaded directly from the SQLite database.
    """

    def __init__(self):
        self.conn = get_connection()

    def get_stock_data(self, stock_id, limit=250):
        """Fetches historical price data for a specific stock into a Pandas DataFrame."""
        query = '''
            SELECT date, open, high, low, close, volume, delivery_percent, delivery_volume
            FROM daily_prices
            WHERE stock_id = ?
            ORDER BY date ASC
            LIMIT ?
        '''
        df = pd.read_sql_query(query, self.conn, params=(stock_id, limit))
        if df.empty:
            return df

        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df

    def calculate_indicators(self, df):
        """
        Calculates all core technical indicators required by the scanner rules.
        """
        if len(df) < 50:
            logger.warning("Not enough data to calculate all indicators robustly (need at least 50 days).")
            # We continue anyway but EMAs might not be fully "warmed up"

        # Moving Averages (EMA 20, 50, 200)
        df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # Relative Volume (compared to 10-day average)
        df['VOL_SMA_10'] = df['volume'].rolling(window=10).mean()
        df['RVOL'] = df['volume'] / df['VOL_SMA_10']

        # Simple RSI (14-day)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))

        return df

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    # Quick test if run directly
    logging.basicConfig(level=logging.INFO)
    engine = IndicatorEngine()
    print("Indicator Engine initialized successfully.")
    engine.close()
