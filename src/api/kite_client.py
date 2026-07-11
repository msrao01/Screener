import os
import logging
from kiteconnect import KiteConnect
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class KiteAPIClient:
    def __init__(self):
        self.api_key = os.getenv('KITE_API_KEY')
        self.api_secret = os.getenv('KITE_API_SECRET')
        self.request_token = os.getenv('KITE_REQUEST_TOKEN')
        self.access_token = None
        self.kite = None

        if not self.api_key or not self.api_secret:
            logger.warning("Kite API credentials not found in environment variables.")

    def initialize(self):
        """Initializes the KiteConnect client and generates the access token."""
        if not self.api_key or not self.api_secret or not self.request_token:
             logger.error("Missing credentials. Please check your .env file.")
             return False

        try:
            self.kite = KiteConnect(api_key=self.api_key)

            # Generate session
            data = self.kite.generate_session(self.request_token, api_secret=self.api_secret)
            self.access_token = data["access_token"]

            # Set access token
            self.kite.set_access_token(self.access_token)
            logger.info("Kite API successfully initialized and authenticated.")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Kite API: {str(e)}")
            return False

    def get_historical_data(self, instrument_token, from_date, to_date, interval="day"):
        """
        Fetches historical data for a given instrument.
        """
        if not self.kite or not self.access_token:
            logger.error("Kite client is not authenticated. Please initialize first.")
            return None

        try:
            records = self.kite.historical_data(instrument_token, from_date, to_date, interval)
            return records
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {instrument_token}: {str(e)}")
            return None

    def search_instruments(self, exchange, symbol):
        """
        Helper method to get instrument token. In production, it's better
        to cache the entire instrument list locally.
        """
        if not self.kite:
             return None

        try:
            instruments = self.kite.instruments(exchange)
            for instr in instruments:
                if instr['tradingsymbol'] == symbol:
                    return instr['instrument_token']
        except Exception as e:
             logger.error(f"Error fetching instrument token for {symbol}: {str(e)}")

        return None

if __name__ == "__main__":
    # Small test snippet
    logging.basicConfig(level=logging.INFO)
    client = KiteAPIClient()
    print("API Key loaded:", bool(client.api_key))
