# Conceptual Data Model

## 1. Overview

The NSE Smart Money Scanner utilizes a relational data model. The initial version will be implemented using **SQLite** for zero-configuration, local-first deployment. The schema is designed conceptually to allow a seamless migration path to **PostgreSQL** in future enterprise or cloud-based iterations.

## 2. Core Entities

The system revolves around several core entities that track market data, analytical results, and user-generated content.

### 2.1 Market Data Entities
* **Stocks (Instruments)**
  * Represents the static universe of NSE equities.
  * Contains metadata such as symbol, company name, sector, and listing status.
* **Daily Prices (OHLCV)**
  * Represents the historical and end-of-day price action.
  * Contains Open, High, Low, Close, and Total Traded Volume.
* **Delivery Data**
  * Tracks the proportion of shares taken for delivery vs. intraday trading.
  * Contains metrics like delivery volume and delivery percentage.

### 2.2 Analytical Entities
* **Indicators**
  * Caches pre-calculated technical indicators (EMA, RSI, MACD) to optimize scan performance.
  * Reduces computational overhead during rapid re-scans.
* **Scan Results**
  * An immutable ledger of historical scan outputs.
  * Captures the stock, the specific scanner rule triggered, the calculated score, and the timestamp.

### 2.3 User Entities
* **Watchlists**
  * User-defined groupings of stocks.
  * Allows a many-to-many relationship mapping specific stocks to specific custom lists.
* **Portfolio**
  * Tracks active and historical user trades.
  * Records entry/exit prices, position sizing, stop-loss/target levels, and realized/unrealized P&L.
* **Settings & Configuration**
  * Stores user preferences, API keys, UI themes, and custom threshold parameters for the scanning engine.
* **Application Logs**
  * An internal audit trail for system events, API failures, and performance metrics.

## 3. High-Level Relationships

* **One-to-Many**:
  * A single `Stock` has many `Daily Prices`.
  * A single `Stock` has many `Delivery Data` records.
  * A single `Stock` has many pre-calculated `Indicators`.
* **Many-to-Many**:
  * `Stocks` and `Watchlists` (A stock can be in multiple watchlists, and a watchlist contains multiple stocks).
* **Historical Tracking**:
  * `Scan Results` act as point-in-time snapshots linking a `Stock` to its performance metrics on a specific date.

## 4. Design Considerations
* **Indexing**: Primary lookups will occur via Stock Symbols and Dates. Compound indexes on these fields are critical for achieving the <5 minute scanning SLA.
* **Data Retention**: Time-series data (OHLCV) will grow over time; the schema must support efficient bulk ingestion for daily updates.
