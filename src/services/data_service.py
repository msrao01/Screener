import logging
import datetime
import urllib.request
import gzip
import csv
import io
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

    def sync_universe_kite(self, cursor):
        """Syncs all NSE Equity symbols using Kite API."""
        self.log_signal.emit("Fetching full NSE Equity instrument list from Kite...")
        all_instruments = self.client.kite.instruments("NSE")

        instrument_map = {}
        db_insert = []

        for instr in all_instruments:
            # We only want regular equities (EQ) for scanning
            if instr['segment'] == 'NSE' and instr['instrument_type'] == 'EQ':
                symbol = instr['tradingsymbol']
                name = instr.get('name', '')
                instrument_map[symbol] = instr['instrument_token']
                db_insert.append((symbol, name))

        self.log_signal.emit(f"Found {len(db_insert)} NSE Equities. Syncing to database...")
        cursor.executemany('INSERT OR IGNORE INTO stocks (symbol, company_name) VALUES (?, ?)', db_insert)
        return instrument_map

    def sync_universe_upstox(self, cursor):
        """Syncs all NSE Equity symbols using Upstox Master Contract CSV."""
        self.log_signal.emit("Downloading Upstox NSE Master Contract CSV...")
        url = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz'

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                with gzip.GzipFile(fileobj=response) as uncompressed:
                    file_content = uncompressed.read().decode('utf-8')

            self.log_signal.emit("Parsing Upstox CSV...")
            reader = csv.DictReader(io.StringIO(file_content))

            instrument_map = {}
            db_insert = []

            for row in reader:
                # Filter for Equities. Upstox CSV format varies, but usually 'instrument_type' is EQ or similar
                # Upstox keys are in 'instrument_key', symbol is in 'tradingsymbol', name in 'name'
                # Ensure it's not a futures/options contract
                symbol = row.get('tradingsymbol')
                instr_key = row.get('instrument_key')
                name = row.get('name', '')
                instr_type = row.get('instrument_type', '')

                if symbol and instr_key and instr_type == 'EQUITY':
                    instrument_map[symbol] = instr_key
                    db_insert.append((symbol, name))

            self.log_signal.emit(f"Found {len(db_insert)} NSE Equities. Syncing to database...")
            cursor.executemany('INSERT OR IGNORE INTO stocks (symbol, company_name) VALUES (?, ?)', db_insert)
            return instrument_map

        except Exception as e:
            self.log_signal.emit(f"ERROR parsing Upstox CSV: {str(e)}")
            return {}

    def run(self):
        self.log_signal.emit(f"Starting Process using {self.broker_type}...")

        # Initialize API
        self.log_signal.emit(f"Authenticating with {self.broker_type}...")
        if not self.client.initialize():
            self.log_signal.emit(f"ERROR: {self.broker_type} authentication failed. Please check your UI credentials and token.")
            self.finished_signal.emit()
            return

        self.log_signal.emit("Authentication successful.")

        conn = get_connection()
        cursor = conn.cursor()

        # Step 1: Sync Universe & Build Instrument Map dynamically
        instrument_map = {}
        if self.broker_type == "Zerodha Kite":
            try:
                instrument_map = self.sync_universe_kite(cursor)
                conn.commit()
            except Exception as e:
                self.log_signal.emit(f"ERROR: Failed to sync Kite universe. {str(e)}")
                conn.close()
                self.finished_signal.emit()
                return
        elif self.broker_type == "Upstox":
            instrument_map = self.sync_universe_upstox(cursor)
            if not instrument_map:
                self.log_signal.emit("ERROR: Failed to build Upstox instrument map.")
                conn.close()
                self.finished_signal.emit()
                return
            conn.commit()

        # Step 2: Get the list of all synced stocks to download EOD data
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

        self.log_signal.emit(f"Fetching historical EOD data from {from_date} to {to_date}")

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
