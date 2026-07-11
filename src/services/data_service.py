import logging
import datetime
from PySide6.QtCore import QThread, Signal
from src.db.database import get_connection
from src.api.kite_client import KiteAPIClient

logger = logging.getLogger(__name__)

class DataDownloadWorker(QThread):
    """
    Background thread for downloading EOD data from Kite API.
    Prevents the PySide6 UI from freezing during network requests.
    """
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self):
        super().__init__()
        self.client = KiteAPIClient()
        self.is_running = True

    def run(self):
        self.log_signal.emit("Starting EOD Data Download Process...")

        # Initialize Kite API
        self.log_signal.emit("Authenticating with Kite API...")
        if not self.client.initialize():
            self.log_signal.emit("ERROR: Authentication failed. Please check your .env file credentials and token.")
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

        # Note: In production, fetching instruments individually per stock is slow and consumes API calls.
        # It's better to fetch the whole list once and map it. For simplicity in this V1 foundation,
        # we will fetch the instrument token for each stock.

        try:
            self.log_signal.emit("Fetching instrument list from NSE...")
            all_instruments = self.client.kite.instruments("NSE")
            instrument_map = {instr['tradingsymbol']: instr['instrument_token'] for instr in all_instruments}
        except Exception as e:
            self.log_signal.emit(f"ERROR: Failed to fetch instrument list. {str(e)}")
            conn.close()
            self.finished_signal.emit()
            return

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
                    date_str = row['date'].strftime("%Y-%m-%d")
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
