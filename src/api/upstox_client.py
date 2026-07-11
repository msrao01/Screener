import os
import logging
import requests
import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class UpstoxAPIClient:
    def __init__(self):
        self.access_token = os.getenv('UPSTOX_ACCESS_TOKEN')
        self.base_url = "https://api.upstox.com/v2"
        self.headers = {
            'accept': 'application/json',
            'Api-Version': '2.0',
        }

    def initialize(self):
        """
        Since the user has a 1-year token, we just need to verify
        that the token exists and is valid by making a profile call.
        """
        if not self.access_token:
            logger.error("Upstox Access Token is missing from environment/UI.")
            return False

        self.headers['Authorization'] = f"Bearer {self.access_token}"

        try:
            # Test authentication by fetching user profile
            response = requests.get(f"{self.base_url}/user/profile", headers=self.headers, timeout=10)

            if response.status_code == 200:
                logger.info("Upstox API successfully initialized and authenticated.")
                return True
            else:
                logger.error(f"Upstox Auth failed: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize Upstox API: {str(e)}")
            return False

    def get_historical_data(self, instrument_key, from_date, to_date, interval="day"):
        """
        Fetches historical data for a given instrument using Upstox v2 API.
        Expected date format from caller: YYYY-MM-DD
        """
        if not self.access_token:
            logger.error("Upstox client is not authenticated.")
            return None

        # Upstox API expects interval format: 1minute, 30minute, day, week, month
        if interval == "day":
            interval = "day" # API accepts "1day" or "day" depending on endpoint, usually "day" for EOD

        try:
            # URL format: /historical-candle/intraday/{instrumentKey}/{interval}/{to_date}/{from_date}
            # Or /historical-candle/{instrumentKey}/{interval}/{to_date}/{from_date}
            # Dates must be in YYYY-MM-DD format
            url = f"{self.base_url}/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"

            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data'] and 'candles' in data['data']:
                    candles = data['data']['candles']
                    # Upstox returns: [timestamp, open, high, low, close, volume, oi]
                    # We need to map it to our expected dictionary format
                    records = []
                    for candle in candles:
                        # parse timestamp: "2023-11-20T00:00:00+05:30"
                        dt = datetime.datetime.fromisoformat(candle[0])
                        records.append({
                            'date': dt,
                            'open': candle[1],
                            'high': candle[2],
                            'low': candle[3],
                            'close': candle[4],
                            'volume': candle[5]
                        })

                    # Sort chronological (Upstox might return newest first)
                    records.sort(key=lambda x: x['date'])
                    return records
                else:
                     logger.warning(f"No candles found for {instrument_key}")
                     return []
            else:
                logger.error(f"Failed to fetch Upstox data for {instrument_key}: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch historical data for {instrument_key}: {str(e)}")
            return None
