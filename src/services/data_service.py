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
from src.api.nse_bhavcopy import NSEBhavcopyClient

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

    def get_official_nse_eq_symbols(self):
        """Downloads the official EQUITY_L.csv from NSE to get the true list of EQ series stocks."""
        self.log_signal.emit("Downloading official NSE Equity list from nsearchives...")
        url = 'https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv'
        valid_symbols = set()

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')

            reader = csv.reader(io.StringIO(content))
            header = next(reader) # Skip header

            for row in reader:
                # Column 0 is SYMBOL, Column 2 is SERIES (with leading/trailing spaces)
                if len(row) > 2 and row[2].strip() == 'EQ':
                    valid_symbols.add(row[0].strip())

            self.log_signal.emit(f"Successfully identified {len(valid_symbols)} official NSE EQ stocks.")
            return valid_symbols

        except Exception as e:
            self.log_signal.emit(f"ERROR downloading official NSE list: {str(e)}")
            return None

    def sync_universe_kite(self, cursor):
        """Syncs all NSE Equity symbols using Kite API."""
        valid_nse_symbols = self.get_official_nse_eq_symbols()
        if not valid_nse_symbols:
            return {}

        self.log_signal.emit("Fetching full NSE instrument list from Kite...")
        all_instruments = self.client.kite.instruments("NSE")

        instrument_map = {}
        db_insert = []

        for instr in all_instruments:
            symbol = instr['tradingsymbol']
            # Cross-reference with the official NSE EQ list
            if instr['segment'] == 'NSE' and symbol in valid_nse_symbols:
                name = instr.get('name', '')
                instrument_map[symbol] = instr['instrument_token']
                db_insert.append((symbol, name))

        self.log_signal.emit(f"Mapped {len(db_insert)} Kite instruments. Syncing to database...")
        cursor.executemany('INSERT OR IGNORE INTO stocks (symbol, company_name) VALUES (?, ?)', db_insert)
        return instrument_map

    def sync_universe_upstox(self, cursor):
        """Syncs all NSE Equity symbols using Upstox Master Contract CSV."""
        valid_nse_symbols = self.get_official_nse_eq_symbols()
        if not valid_nse_symbols:
            return {}

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
                symbol = row.get('tradingsymbol')
                instr_key = row.get('instrument_key')
                name = row.get('name', '')

                # Cross-reference with the official NSE EQ list
                if symbol and instr_key and (symbol in valid_nse_symbols):
                    instrument_map[symbol] = instr_key
                    db_insert.append((symbol, name))

            self.log_signal.emit(f"Mapped {len(db_insert)} Upstox instruments. Syncing to database...")
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

        # Clean up old junk non-EQ stocks that might be stuck in the database from previous runs
        if instrument_map:
            valid_symbols = list(instrument_map.keys())
            placeholders = ','.join(['?'] * len(valid_symbols))
            self.log_signal.emit("Cleaning up obsolete/non-EQ symbols from database...")
            try:
                # Delete daily_prices for stocks not in the valid list
                cursor.execute(f"DELETE FROM daily_prices WHERE stock_id IN (SELECT id FROM stocks WHERE symbol NOT IN ({placeholders}))", valid_symbols)
                # Delete stocks not in the valid list
                cursor.execute(f"DELETE FROM stocks WHERE symbol NOT IN ({placeholders})", valid_symbols)
                conn.commit()
            except Exception as e:
                self.log_signal.emit(f"Database cleanup warning: {str(e)}")

        # Step 2: Get the list of all synced stocks to download EOD data
        cursor.execute("SELECT id, symbol FROM stocks")
        stocks = cursor.fetchall()

        if not stocks:
            self.log_signal.emit("No stocks found in database to process.")
            conn.close()
            self.finished_signal.emit()
            return

        # Setup date range to exactly 365 days to ensure EMA-200 can be calculated
        to_date = datetime.datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")

        self.log_signal.emit(f"Fetching historical EOD data from {from_date} to {to_date}")

        processed_count = 0
        skipped_count = 0
        total_records_inserted = 0

        for stock in stocks:
            if not self.is_running:
                self.log_signal.emit("Download cancelled by user.")
                break

            stock_id = stock['id']
            symbol = stock['symbol']

            instrument_token = instrument_map.get(symbol)
            if not instrument_token:
                # We skip silently here to avoid spamming the log with expected BE/BZ series omissions
                skipped_count += 1
                continue

            processed_count += 1
            if processed_count % 100 == 0:
                self.log_signal.emit(f"Progress: Downloaded EOD data for {processed_count} valid stocks...")

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
                        INSERT INTO daily_prices (stock_id, date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(stock_id, date) DO UPDATE SET
                            open=excluded.open,
                            high=excluded.high,
                            low=excluded.low,
                            close=excluded.close,
                            volume=excluded.volume
                    ''', insert_data)
                    conn.commit()
                    total_records_inserted += len(records)
                except Exception as e:
                     self.log_signal.emit(f"Database error for {symbol}: {str(e)}")

        self.log_signal.emit(f"--- OHLCV Download Complete ---")
        self.log_signal.emit(f"Total valid stocks processed: {processed_count}")
        self.log_signal.emit(f"Total non-EQ instruments skipped: {skipped_count}")
        self.log_signal.emit(f"Total daily records saved: {total_records_inserted}")

        # Step 3: Fetch Delivery Data from NSE Bhavcopy to enrich the OHLCV data
        self.log_signal.emit("Starting NSE Delivery Data Sync...")
        bhavcopy_client = NSEBhavcopyClient()

        # We only need to fetch bhavcopies for the most recent few trading dates.
        # Historical delivery data from 300 days ago is irrelevant for today's scanner logic.
        # Fetching only the last 3 dates ensures high speed (takes 3 seconds instead of 10 minutes).
        cursor.execute("SELECT DISTINCT date FROM daily_prices WHERE date >= ? ORDER BY date DESC LIMIT 3", (from_date,))
        active_dates = [row['date'] for row in cursor.fetchall()]

        for date_str in active_dates:
            if not self.is_running:
                break

            self.log_signal.emit(f"Fetching NSE Delivery Data for {date_str}...")
            delivery_data = bhavcopy_client.fetch_delivery_data(date_str)

            if delivery_data:
                # Update the database
                update_records = []
                for symbol, data in delivery_data.items():
                    # We only update stocks that we actually track in our universe
                    stock_id_query = "SELECT id FROM stocks WHERE symbol = ?"
                    cursor.execute(stock_id_query, (symbol,))
                    res = cursor.fetchone()
                    if res:
                        update_records.append((
                            data['delivery_volume'],
                            data['delivery_percent'],
                            res['id'],
                            date_str
                        ))

                try:
                    cursor.executemany('''
                        UPDATE daily_prices
                        SET delivery_volume = ?, delivery_percent = ?
                        WHERE stock_id = ? AND date = ?
                    ''', update_records)
                    conn.commit()
                    self.log_signal.emit(f"Updated delivery data for {len(update_records)} stocks on {date_str}.")
                except Exception as e:
                    self.log_signal.emit(f"Database error updating delivery data: {str(e)}")
            else:
                self.log_signal.emit(f"No delivery data found/available for {date_str}.")

        conn.close()
        self.log_signal.emit("--- Full Data Sync Complete ---")
        self.finished_signal.emit()

    def stop(self):
        """Stops the worker thread safely."""
        self.is_running = False
