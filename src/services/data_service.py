import logging
import datetime
from PySide6.QtCore import QThread, Signal
from src.db.database import get_connection
from src.api.kite_client import KiteAPIClient
from src.api.upstox_client import UpstoxAPIClient

logger = logging.getLogger(__name__)

class DataDownloadWorker(QThread):
    """
    Background thread for downloading EOD data from the selected API.
    Prevents the PySide6 UI from freezing during network requests.
    """
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, broker_type="Zerodha Kite"):
        super().__init__()
        self.broker_type = broker_type
        if self.broker_type == "Upstox":
            self.client = UpstoxAPIClient()
        else:
            self.client = KiteAPIClient()
        self.is_running = True

    def run(self):
        self.log_signal.emit(f"Starting EOD Data Download Process using {self.broker_type}...")

        # Initialize API
        self.log_signal.emit(f"Authenticating with {self.broker_type}...")
        if not self.client.initialize():
            self.log_signal.emit(f"ERROR: {self.broker_type} authentication failed. Please check your UI credentials and token.")
            self.finished_signal.emit()
            return

        self.log_signal.emit("Authentication successful.")

        # Connect to Database and get stocks
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, symbol FROM stocks")
        stocks = cursor.fetchall()

        if not stocks:
            self.log_signal.emit("No stocks found in database to process.")
            conn.close()
            self.finished_signal.emit()
            return

        # Setup date range (e.g., last 30 days)
        to_date = datetime.datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

        self.log_signal.emit(f"Fetching data from {from_date} to {to_date}")

        # We need an instrument map for the broker
        instrument_map = {}
        if self.broker_type == "Zerodha Kite":
            try:
                self.log_signal.emit("Fetching instrument list from Kite...")
                all_instruments = self.client.kite.instruments("NSE")
                instrument_map = {instr['tradingsymbol']: instr['instrument_token'] for instr in all_instruments}
            except Exception as e:
                self.log_signal.emit(f"ERROR: Failed to fetch Kite instrument list. {str(e)}")
                conn.close()
                self.finished_signal.emit()
                return
        elif self.broker_type == "Upstox":
            # For Upstox V2, instrument keys look like NSE_EQ|INE002A01018 (or using symbol mapping).
            # Upstox provides a master contract CSV. For this foundation, we'll use a hardcoded map
            # for the 10 seeded NIFTY 50 stocks to demonstrate functionality.
            self.log_signal.emit("Using local Upstox instrument mapping...")
            instrument_map = {
                'RELIANCE': 'NSE_EQ|INE002A01018',
                'TCS': 'NSE_EQ|INE467B01029',
                'HDFCBANK': 'NSE_EQ|INE040A01034',
                'INFY': 'NSE_EQ|INE009A01021',
                'ICICIBANK': 'NSE_EQ|INE090A01021',
                'HUL': 'NSE_EQ|INE030A01027', # Actually HINDUNILVR
                'ITC': 'NSE_EQ|INE154A01025',
                'SBIN': 'NSE_EQ|INE062A01020',
                'BHARTIARTL': 'NSE_EQ|INE397D01024',
                'BAJFINANCE': 'NSE_EQ|INE296A01024'
            }

        for stock in stocks:
            if not self.is_running:
                self.log_signal.emit("Download cancelled by user.")
                break

            stock_id = stock['id']
            symbol = stock['symbol']

            instrument_token = instrument_map.get(symbol)
            if not instrument_token:
                self.log_signal.emit(f"Skipping {symbol}: Instrument token not found.")
                continue

            self.log_signal.emit(f"Downloading EOD data for {symbol}...")

            records = self.client.get_historical_data(instrument_token, from_date, to_date, "day")

            if records:
                # Insert into database
                insert_data = []
                for row in records:
                    if isinstance(row['date'], datetime.datetime):
                         date_str = row['date'].strftime("%Y-%m-%d")
                    else:
                         date_str = row['date'] # If it's already a string

                    insert_data.append((
                        stock_id, date_str,
                        row['open'], row['high'], row['low'], row['close'], row['volume']
                    ))

                try:
                    cursor.executemany('''
                        INSERT OR IGNORE INTO daily_prices (stock_id, date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', insert_data)
                    conn.commit()
                    self.log_signal.emit(f"Saved {len(records)} records for {symbol}.")
                except Exception as e:
                     self.log_signal.emit(f"Database error for {symbol}: {str(e)}")
            else:
                 self.log_signal.emit(f"No data received for {symbol}.")

        conn.close()
        self.log_signal.emit("EOD Data Download Process Finished.")
        self.finished_signal.emit()

    def stop(self):
        """Stops the worker thread safely."""
        self.is_running = False
