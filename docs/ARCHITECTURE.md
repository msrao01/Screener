# System Architecture

## 1. Overview

The NSE Smart Money Scanner is designed as a standalone Windows desktop application utilizing a modern layered architecture. The system ensures a strict separation of concerns between the user interface, business logic, and underlying data persistence. This modular approach guarantees that the application remains maintainable, testable, and scalable as future features (such as cloud synchronization or alternative data providers) are introduced.

## 2. High-Level Architectural Diagram

```text
+----------------------------------------------------------+
|                    Presentation Layer                    |
|                 PySide6 Desktop Application              |
+----------------------------------------------------------+
                           |
                           v
+----------------------------------------------------------+
|                 Application Services                     |
|  Scanner | Portfolio | Watchlist | Reports | Settings    |
+----------------------------------------------------------+
                           |
                           v
+----------------------------------------------------------+
|                  Domain / Business Logic                 |
| Indicators | Rules | Scoring | Signal Engine             |
+----------------------------------------------------------+
                           |
                           v
+----------------------------------------------------------+
|                 Infrastructure Layer                     |
| SQLite | Upstox | NSE Import | Logging | Configuration   |
+----------------------------------------------------------+
```

## 3. Layer Descriptions

### 3.1 Presentation Layer
**Responsibility**: Managing user interactions, rendering visual components, and capturing user input.
* **Technology**: Python with the `PySide6` framework.
* **Design Pattern**: Model-View-ViewModel (MVVM) or Model-View-Controller (MVC) paradigms will be leveraged to decouple UI components from the underlying business state.
* **Components**:
  * Main Application Window
  * Interactive Dashboards
  * Asynchronous UI updates (ensuring the main thread is never blocked by the scanner engine).
  * High-performance charting interfaces.

### 3.2 Application Services Layer
**Responsibility**: Orchestrating application workflows and acting as the mediator between the Presentation and Domain layers.
* **Components**:
  * **Scanner Service**: Manages the lifecycle of a scan, delegating calculation to the Domain layer and progress updates to the UI.
  * **Portfolio & Watchlist Services**: Manages the CRUD operations for user-defined lists and trade tracking.
  * **Reporting Service**: Formats domain data into exportable outputs (CSV, PDF).

### 3.3 Domain / Business Logic Layer
**Responsibility**: Encapsulating all proprietary business rules, mathematical calculations, and scoring mechanics. This layer is entirely agnostic of the UI and Database.
* **Components**:
  * **Indicator Engine**: Calculates technical metrics (EMA, MACD, RSI, ATR) securely and efficiently.
  * **Rules Engine**: Evaluates individual stock profiles against defined strategies (e.g., Institutional Accumulation, Pullback).
  * **Scoring Engine**: Applies the weighted 100-point grading system to prioritize opportunities.

### 3.4 Infrastructure Layer
**Responsibility**: Managing all external I/O, including database interactions, external API communication, and local file management.
* **Components**:
  * **Data Access**: Interfaces with the local SQLite database. Abstracted in a way that allows future migration to PostgreSQL.
  * **Market Data Ingestion**: Handles API communication with external brokers (e.g., Upstox) and parses end-of-day NSE delivery files.
  * **Telemetry & Logging**: Centralized logging for system health, performance metrics, and error tracking.

## 4. Key Architectural Decisions

1. **Local-First Processing**: To ensure speed and privacy, V1 handles all scanning and data persistence locally on the user's machine via SQLite.
2. **Asynchronous Execution**: Heavy I/O (database queries, network requests) and heavy CPU tasks (scanning 2000+ stocks) are offloaded to background threads to maintain a fluid PySide6 UI.
3. **Modular Rule Engine**: The scanner logic is designed via abstract interfaces, allowing developers to add new patterns (like VCP or Minervini) without altering the core execution loop.
