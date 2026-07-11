# Software Requirements Specification (SRS)

## 1. Executive Summary

**Project Name**: NSE Smart Money Scanner
**Version**: 1.0
**Platform**: Windows Desktop
**Core Technologies**: Python, PySide6
**Database**: SQLite (v1) -> PostgreSQL (Future)

### 1.1 Purpose
The NSE Smart Money Scanner is a desktop application engineered to automate the scanning of all NSE-listed equities. The system identifies institutional accumulation patterns and presents high-probability swing trading opportunities through an intuitive, interactive interface. Its primary goal is to compress hours of manual market screening into minutes, while providing transparent, rule-based justifications for every qualified stock.

## 2. Objectives

### 2.1 Primary Objectives
* **Comprehensive Scanning**: Evaluate all NSE equities efficiently.
* **Pattern Detection**: Automatically detect institutional accumulation, breakouts, and pullbacks.
* **Algorithmic Ranking**: Rank stocks using a proprietary confidence scoring engine.
* **Professional Charting**: Render high-performance, interactive charts with embedded indicators.
* **Historical Tracking**: Maintain an immutable history of daily scan results for historical analysis.

### 2.2 Secondary Objectives
* Portfolio tracking and performance analysis.
* Trade journaling for continuous improvement.
* Customizable watchlists for continuous monitoring.
* System alerts for key price action events.
* Backtesting capabilities to validate strategies.

## 3. Target Audience
* **Swing Traders & Position Traders**: Seeking high-probability setups over multi-day or multi-week timeframes.
* **Technical Analysts**: Requiring robust charting and automated technical indicator screening.
* **Self-Directed Retail Investors**: Looking to automate manual research processes.

## 4. Functional Requirements

### 4.1 Authentication & Access
* **Version 1.0**: Standalone desktop operation; no authentication required.
* **Future Iterations**: Brokerage OAuth integration (e.g., Upstox) for live data and trade execution.

### 4.2 Executive Dashboard
Provides a macro-level overview of the market and application state.
* **KPI Metrics**: Total NSE stocks, scanned stocks, and qualified stocks.
* **Market Breadth**: Number of institutional candidates, breakouts, pullbacks, high delivery, and high volume stocks.
* **System Status**: Last scan timestamp and data freshness.

### 4.3 Scanner Engine
The core execution engine responsible for evaluating the market.
* **Process**: Automates the sequential scanning, calculation of technical indicators, and application of business rules across the equity universe.
* **Output**: Scores, ranks, and filters stocks based on confidence thresholds.

### 4.4 Stock Detail View
A comprehensive view of an individual equity's technical health.
* **Core Metrics**: OHLC, Volume, Delivery Percentage, Relative Volume.
* **Technical Indicators**: EMA (20, 50, 200), RSI, MACD, ATR.
* **Trade Parameters**: Calculated Breakout levels, Entry points, Stop-loss limits, and Target prices.

### 4.5 Interactive Charting
Professional-grade candlestick charting interface.
* **Visuals**: Candlesticks, EMAs, Volume bars, VWAP, and calculated breakout/entry/stop/target lines.
* **Interactivity**: Fluid zooming, panning, crosshair inspection, and dynamic timeframe selection.

### 4.6 Watchlist Management
* Functionality to create, rename, and manage multiple user-defined watchlists.
* Seamless addition and removal of stocks from scanner results.

### 4.7 Portfolio Tracking
* Maintains a ledger of user trades, tracking Entry/Exit prices, Quantities, Stop-loss/Targets, P&L, and Holding periods.

### 4.8 Alerting System
* Desktop notifications for triggered events.
* **Future**: Webhooks for Telegram and Email notifications.

### 4.9 Reporting Engine
* Generates actionable reports including Daily Scan Summaries, Top Breakouts, and Portfolio Performance.
* Export capabilities to standard formats (CSV, Excel, PDF).

## 5. Scanner Rule Definitions

The scanner utilizes distinct rule sets to identify specific market behaviors.

### 5.1 Scanner 1: Institutional Accumulation
Identifies footprints of large capital entry.
* **Criteria**: Short-term trend > Long-term trend (EMA20 > EMA50), Price above short-term trend, Volume > 2x Average, High Delivery (>60%), and strong closing price.

### 5.2 Scanner 2: Breakout
Identifies momentum-driven price expansion.
* **Criteria**: Price closing above the 20-day high, elevated volume (>2x), and strong momentum (RSI > 55).

### 5.3 Scanner 3: Pullback
Identifies low-risk entry points within an established trend.
* **Criteria**: Established uptrend (EMA20 > EMA50), price retesting short-term trend line, accompanied by a bullish candlestick formation and above-average volume.

### 5.4 Future Scanners
* Volatility Contraction Pattern (VCP).
* Minervini Trend Template.

## 6. Scoring Engine
A proprietary weighted engine out of 100 maximum points.

**Weight Distribution**:
* EMA Trend: 25%
* Relative Volume: 20%
* Breakout Confirmation: 20%
* Delivery Strength: 15%
* Trend Strength: 10%
* Strong Close: 10%

**Grading Tiers**:
* 90–100: Exceptional (⭐⭐⭐⭐⭐)
* 75–89: Strong (⭐⭐⭐⭐)
* 60–74: Moderate (⭐⭐⭐)
* Below 60: Discard

## 7. Non-Functional Requirements

### 7.1 Performance
* **Scan Speed**: Process 2,000+ NSE stocks in under 5 minutes on standard consumer hardware.
* **UI Responsiveness**: Load scanner results in under 2 seconds.
* **Chart Rendering**: Refresh in under 500 milliseconds upon stock selection.

### 7.2 Reliability & Fault Tolerance
* Zero data loss upon unexpected application termination.
* Graceful degradation during API rate limits or missing market data.
* Strict validation of imported data files prior to processing.

### 7.3 Usability
* Native dark mode for reduced eye strain.
* Comprehensive keyboard shortcuts for power users.
* Asynchronous processing to guarantee the UI remains unblocked during heavy computation.

### 7.4 Security
* Secure, encrypted local storage for any required API tokens.
* Strict prohibition on logging sensitive credentials.

## 8. Future Roadmap Features
* **AI Analysis**: Automated pattern recognition (Cup & Handle, Darvas Box).
* **Market Context**: Sector rotation analysis and Relative Strength tracking against the NIFTY index.
* **Fundamental Overlays**: Earnings calendar integration and FII/DII flow analysis.
* **Ecosystem**: Cloud synchronization and a companion mobile application.
