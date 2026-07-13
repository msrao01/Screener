import requests
import datetime
import csv
import io
import logging

logger = logging.getLogger(__name__)

class NSEBhavcopyClient:
    """
    Downloads and parses the official NSE daily Bhavcopy (sec_bhavdata_full)
    to extract Delivery Volume and Delivery Percentage for all EQ series stocks.
    """

    def __init__(self):
        # NSE requires standard browser headers to prevent blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _get_cookie(self):
        """NSE sometimes requires an initial visit to set a session cookie."""
        try:
            self.session.get("https://www.nseindia.com", timeout=10)
        except Exception as e:
            logger.warning(f"Failed to fetch NSE initial cookies: {e}")

    def fetch_delivery_data(self, date_str):
        """
        Fetches the full bhavcopy for a given date (YYYY-MM-DD).
        Returns a dictionary mapping:
        { "SYMBOL": {"delivery_volume": int, "delivery_percent": float} }
        """
        # Parse date to NSE's format: DDMMYYYY
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        nse_date = dt.strftime("%d%m%Y")

        url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{nse_date}.csv"

        self._get_cookie()

        try:
            response = self.session.get(url, timeout=15)

            # 404 usually means it was a weekend or market holiday
            if response.status_code == 404:
                return None

            if response.status_code != 200:
                logger.error(f"NSE Bhavcopy returned status {response.status_code} for {date_str}")
                return None

            content = response.text
            reader = csv.DictReader(io.StringIO(content))

            delivery_map = {}

            for row in reader:
                # Column headers often have trailing/leading spaces in NSE files
                series = row.get(' SERIES', '').strip()
                if series == 'EQ':
                    symbol = row.get('SYMBOL', '').strip()
                    deliv_qty_str = row.get(' DELIV_QTY', '').strip()
                    deliv_per_str = row.get(' DELIV_PER', '').strip()

                    if symbol and deliv_qty_str and deliv_qty_str != '-':
                        try:
                            delivery_map[symbol] = {
                                'delivery_volume': int(deliv_qty_str),
                                'delivery_percent': float(deliv_per_str) if deliv_per_str != '-' else 0.0
                            }
                        except ValueError:
                            pass

            return delivery_map

        except Exception as e:
            logger.error(f"Error fetching NSE Bhavcopy for {date_str}: {e}")
            return None

if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    client = NSEBhavcopyClient()

    # Let's try to get data for yesterday or last friday
    # Since today's date in sandbox is 2026-07-12 (Sunday), Friday was 2026-07-10
    test_date = "2026-07-10"
    data = client.fetch_delivery_data(test_date)

    if data:
        print(f"Successfully fetched delivery data for {len(data)} EQ stocks on {test_date}")
        if 'RELIANCE' in data:
            print(f"Reliance: {data['RELIANCE']}")
    else:
        print(f"No data available for {test_date} (possibly a holiday/weekend or future date).")
