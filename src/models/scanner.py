import logging
import pandas as pd
from src.db.database import get_connection
from src.models.indicators import IndicatorEngine

logger = logging.getLogger(__name__)

class ScannerEngine:
    """
    Implements the core business logic (Milestone 4):
    Evaluates stocks against rules (Institutional Accumulation, Breakout, Pullback)
    and applies the 100-point proprietary scoring system.
    """
    def __init__(self):
        self.indicator_engine = IndicatorEngine()

    def score_stock(self, df):
        """
        Applies the proprietary 100-point scoring engine.
        Weights: EMA Trend (25), RVOL (20), Breakout Confirm (20), Delivery (15), Trend Strength (10), Strong Close (10)
        """
        score = 0
        latest = df.iloc[-1]

        # 1. EMA Trend (25 points): Short > Medium > Long
        if latest['EMA_20'] > latest['EMA_50'] and latest['EMA_50'] > latest['EMA_200']:
            score += 25
        elif latest['EMA_20'] > latest['EMA_50']:
            score += 15 # Partial credit

        # 2. Relative Volume (20 points): Elevated volume
        if latest['RVOL'] > 2.0:
            score += 20
        elif latest['RVOL'] > 1.5:
            score += 10 # Partial credit

        # 3. Breakout Confirmation (20 points): Close near high
        # Calculate how close the closing price is to the high of the day (upper 20% of range)
        range_high_low = latest['high'] - latest['low']
        if range_high_low > 0:
            close_pos = (latest['close'] - latest['low']) / range_high_low
            if close_pos > 0.80:
                score += 20
            elif close_pos > 0.60:
                score += 10

        # 4. Delivery Strength (15 points)
        # Using 60% as exceptional delivery threshold based on SRS
        delivery_pct = latest.get('delivery_percent', 0.0)
        if delivery_pct > 60.0:
            score += 15
        elif delivery_pct > 45.0:
            score += 8

        # 5. Trend Strength / Momentum (10 points)
        if latest['RSI_14'] > 55 and latest['RSI_14'] < 80:
            score += 10

        # 6. Strong Close vs Open (10 points)
        if latest['close'] > latest['open']:
            if (latest['close'] - latest['open']) / latest['open'] > 0.02: # 2% up day
                score += 10
            else:
                score += 5

        return score

    def determine_grade(self, score):
        if score >= 90:
            return "Exceptional (⭐⭐⭐⭐⭐)"
        elif score >= 75:
            return "Strong (⭐⭐⭐⭐)"
        elif score >= 60:
            return "Moderate (⭐⭐⭐)"
        return "Discard"

    def scan_institutional_accumulation(self, df):
        """
        Criteria: EMA20 > EMA50, Price > EMA20, RVOL > 2x, High Delivery (>60%), Strong Close.
        """
        latest = df.iloc[-1]
        if (latest['EMA_20'] > latest['EMA_50'] and
            latest['close'] > latest['EMA_20'] and
            latest['RVOL'] > 2.0 and
            latest.get('delivery_percent', 0.0) > 60.0 and
            latest['close'] > latest['open']):
            return True
        return False

    def scan_breakout(self, df):
        """
        Criteria: Price closing above 20-day high, elevated volume (>2x), RSI > 55
        """
        latest = df.iloc[-1]
        # Calculate 20-day high excluding today
        if len(df) > 20:
            high_20d = df['high'].iloc[-21:-1].max()
            if (latest['close'] > high_20d and
                latest['RVOL'] > 2.0 and
                latest['RSI_14'] > 55):
                return True
        return False

    def scan_pullback(self, df):
        """
        Criteria: Established uptrend (EMA20 > EMA50), price retesting EMA20, bullish candle, above avg volume.
        """
        latest = df.iloc[-1]
        if latest['EMA_20'] > latest['EMA_50']:
            # Retest: Low dipped below or near EMA20, but close is above
            is_retest = latest['low'] <= (latest['EMA_20'] * 1.01) and latest['close'] > latest['EMA_20']
            bullish_candle = latest['close'] > latest['open']
            if is_retest and bullish_candle and latest['RVOL'] > 1.0:
                return True
        return False

    def run_full_scan(self):
        """
        Executes the scan across all available stocks.
        Returns a list of dictionaries with the results.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, symbol FROM stocks")
        stocks = cursor.fetchall()
        conn.close()

        results = []

        for stock in stocks:
            df = self.indicator_engine.get_stock_data(stock['id'], limit=250)
            if df.empty or len(df) < 25:
                continue # Not enough data

            # Apply Indicators
            df = self.indicator_engine.calculate_indicators(df)

            # Run Scanners
            scanners_matched = []
            if self.scan_institutional_accumulation(df):
                scanners_matched.append("Inst. Accumulation")
            if self.scan_breakout(df):
                scanners_matched.append("Breakout")
            if self.scan_pullback(df):
                scanners_matched.append("Pullback")

            # Score
            score = self.score_stock(df)
            grade = self.determine_grade(score)

            if scanners_matched or grade != "Discard":
                results.append({
                    "symbol": stock['symbol'],
                    "scanners": ", ".join(scanners_matched) if scanners_matched else "None",
                    "score": score,
                    "grade": grade,
                    "close_price": round(df.iloc[-1]['close'], 2),
                    "rvol": round(df.iloc[-1]['RVOL'], 2),
                    "delivery": round(df.iloc[-1].get('delivery_percent', 0.0), 2)
                })

        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

if __name__ == "__main__":
    engine = ScannerEngine()
    print("Scanner Engine Ready.")
