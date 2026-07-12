import sys
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QTextEdit, QHBoxLayout,
    QComboBox, QFormLayout, QLineEdit, QGroupBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
import os
from dotenv import set_key
from PySide6.QtCore import Qt, QThread, Signal
from src.services.data_service import DataDownloadWorker
from src.models.scanner import ScannerEngine
from src.db.database import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScannerWorker(QThread):
    finished_signal = Signal(list)
    log_signal = Signal(str)

    def run(self):
        self.log_signal.emit("Initializing Scanner Engine...")
        engine = ScannerEngine()
        self.log_signal.emit("Running full market scan. This may take a moment...")
        results = engine.run_full_scan()
        self.log_signal.emit(f"Scan complete. Evaluated {len(results)} qualified stocks.")
        self.finished_signal.emit(results)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NSE Smart Money Scanner")

        # Apply Modern Dark Theme
        self.apply_dark_theme()

        # Main Widget and Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # Left Panel (Settings & Controls)
        self.left_panel = QWidget()
        self.left_panel.setFixedWidth(350)
        self.left_layout = QVBoxLayout(self.left_panel)

        # Header
        self.header_label = QLabel("Scanner Configuration")
        self.header_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        self.left_layout.addWidget(self.header_label)

        # Broker Settings Group
        self.broker_group = QGroupBox("Broker Connection")
        self.broker_layout = QFormLayout()

        self.broker_combo = QComboBox()
        self.broker_combo.addItems(["Zerodha Kite", "Upstox"])
        self.broker_combo.currentTextChanged.connect(self.on_broker_changed)
        self.broker_layout.addRow("Provider:", self.broker_combo)

        self.api_key_input = QLineEdit()
        self.broker_layout.addRow("API Key:", self.api_key_input)

        self.api_secret_input = QLineEdit()
        self.api_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.broker_layout.addRow("API Secret:", self.api_secret_input)

        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_label = QLabel("Token:")
        self.broker_layout.addRow(self.token_label, self.token_input)

        self.save_button = QPushButton("Save Credentials")
        self.save_button.clicked.connect(self.save_credentials)
        self.broker_layout.addRow("", self.save_button)

        self.broker_group.setLayout(self.broker_layout)
        self.left_layout.addWidget(self.broker_group)

        # Load initial credentials
        self.on_broker_changed(self.broker_combo.currentText())

        self.left_layout.addStretch()

        # Download Button
        self.download_button = QPushButton("1. SYNC UNIVERSE & DOWNLOAD DATA")
        self.download_button.setMinimumHeight(40)
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px;
            }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:disabled { background-color: #7f8c8d; }
        """)
        self.download_button.clicked.connect(self.start_download)
        self.left_layout.addWidget(self.download_button)

        # Scan Button
        self.scan_button = QPushButton("2. RUN SMART MONEY SCANNER")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.setStyleSheet("""
            QPushButton {
                background-color: #8e44ad; color: white; font-weight: bold; border-radius: 4px; margin-top: 10px;
            }
            QPushButton:hover { background-color: #9b59b6; }
            QPushButton:disabled { background-color: #7f8c8d; }
        """)
        self.scan_button.clicked.connect(self.start_scan)
        self.left_layout.addWidget(self.scan_button)

        self.main_layout.addWidget(self.left_panel)

        # Right Panel (Tabs)
        self.tabs = QTabWidget()

        # All Stocks Tab
        self.all_stocks_tab = QWidget()
        self.all_stocks_layout = QVBoxLayout(self.all_stocks_tab)
        self.all_stocks_table = QTableWidget()
        self.all_stocks_table.setColumnCount(2)
        self.all_stocks_table.setHorizontalHeaderLabels(["Symbol", "Company Name"])
        self.all_stocks_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.all_stocks_table.setAlternatingRowColors(True)
        self.all_stocks_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.all_stocks_table.setShowGrid(False)
        self.all_stocks_layout.addWidget(self.all_stocks_table)
        self.tabs.addTab(self.all_stocks_tab, "All NSE Stocks")

        # Scanner Results Tab
        self.results_tab = QWidget()
        self.results_layout = QVBoxLayout(self.results_tab)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Symbol", "Close", "Matched Scanner", "Score", "Grade", "RVOL", "Delivery %"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setShowGrid(False)
        self.results_layout.addWidget(self.results_table)
        self.tabs.addTab(self.results_tab, "Scanner Results")

        # Log Tab
        self.log_tab = QWidget()
        self.log_layout = QVBoxLayout(self.log_tab)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #1e1e1e; color: #ecf0f1; font-family: Consolas;")
        self.log_layout.addWidget(self.log_area)
        self.tabs.addTab(self.log_tab, "Execution Logs")

        self.main_layout.addWidget(self.tabs)

        # Populate All Stocks tab initially
        self.load_all_stocks()

        self.download_worker = None
        self.scan_worker = None

        self.log_message("Application Initialized.")
        self.log_message("1. Sync Universe to update database.")
        self.log_message("2. Run Scanner to analyze the market.")

    def apply_dark_theme(self):
        """Applies a global professional dark theme to the application, resembling a trading terminal."""
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QWidget { color: #e0e0e0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }

            QGroupBox {
                border: 1px solid #333333;
                border-radius: 8px;
                margin-top: 20px;
                background-color: #1a1a1a;
                font-weight: bold;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 0 5px;
                color: #bbbbbb;
            }

            QLineEdit, QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
                selection-background-color: #3498db;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #3498db; background-color: #222222; }

            QPushButton {
                background-color: #2980b9;
                color: white;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #3498db; }
            QPushButton:pressed { background-color: #1f618d; }

            QTabWidget::pane {
                border: 1px solid #333333;
                background-color: #1a1a1a;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2a2a2a;
                color: #888888;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #1a1a1a;
                color: #ffffff;
                border-bottom: 2px solid #3498db;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #333333;
                color: #dddddd;
            }

            QTableWidget {
                background-color: #1a1a1a;
                alternate-background-color: #222222;
                color: #e0e0e0;
                gridline-color: transparent;
                border: none;
                selection-background-color: #2c3e50;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #aaaaaa;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #444444;
                padding: 5px;
                text-align: left;
            }
            QTableCornerButton::section { background-color: #252525; border: none; }

            QTextEdit {
                background-color: #121212;
                color: #bbbbbb;
                font-family: 'Consolas', 'Courier New', monospace;
                border: none;
                padding: 10px;
            }
        """)

    def on_broker_changed(self, broker_name):
        if broker_name == "Zerodha Kite":
            self.token_label.setText("Daily Request Token:")
            self.api_key_input.setText(os.getenv("KITE_API_KEY", ""))
            self.api_secret_input.setText(os.getenv("KITE_API_SECRET", ""))
            self.token_input.setText(os.getenv("KITE_REQUEST_TOKEN", ""))
        elif broker_name == "Upstox":
            self.token_label.setText("1-Year Access Token:")
            self.api_key_input.setText(os.getenv("UPSTOX_API_KEY", ""))
            self.api_secret_input.setText(os.getenv("UPSTOX_API_SECRET", ""))
            self.token_input.setText(os.getenv("UPSTOX_ACCESS_TOKEN", ""))

    def save_credentials(self):
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        # If file doesn't exist, create it
        if not os.path.exists(env_file):
            with open(env_file, 'w') as f:
                f.write('')

        broker = self.broker_combo.currentText()
        if broker == "Zerodha Kite":
            set_key(env_file, "KITE_API_KEY", self.api_key_input.text())
            set_key(env_file, "KITE_API_SECRET", self.api_secret_input.text())
            set_key(env_file, "KITE_REQUEST_TOKEN", self.token_input.text())
            os.environ["KITE_API_KEY"] = self.api_key_input.text()
            os.environ["KITE_API_SECRET"] = self.api_secret_input.text()
            os.environ["KITE_REQUEST_TOKEN"] = self.token_input.text()
        elif broker == "Upstox":
            set_key(env_file, "UPSTOX_API_KEY", self.api_key_input.text())
            set_key(env_file, "UPSTOX_API_SECRET", self.api_secret_input.text())
            set_key(env_file, "UPSTOX_ACCESS_TOKEN", self.token_input.text())
            os.environ["UPSTOX_API_KEY"] = self.api_key_input.text()
            os.environ["UPSTOX_API_SECRET"] = self.api_secret_input.text()
            os.environ["UPSTOX_ACCESS_TOKEN"] = self.token_input.text()

        self.log_message(f"Credentials saved for {broker}.")

    def load_all_stocks(self):
        """Loads all stocks from the local database into the All Stocks tab."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT symbol, company_name FROM stocks ORDER BY symbol ASC")
            stocks = cursor.fetchall()
            conn.close()

            self.all_stocks_table.setRowCount(0)
            for i, row in enumerate(stocks):
                self.all_stocks_table.insertRow(i)
                self.all_stocks_table.setItem(i, 0, QTableWidgetItem(row['symbol']))
                self.all_stocks_table.setItem(i, 1, QTableWidgetItem(row['company_name']))
        except Exception as e:
            self.log_message(f"Could not load all stocks: {str(e)}")

    def log_message(self, message):
        """Appends a message to the status area."""
        self.log_area.append(message)
        logger.info(message)

    def start_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.log_message("A download process is already running.")
            return

        self.tabs.setCurrentIndex(2) # Switch to logs tab
        self.download_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.log_area.clear()

        broker_type = self.broker_combo.currentText()
        self.download_worker = DataDownloadWorker(broker_type=broker_type)
        self.download_worker.log_signal.connect(self.log_message)
        self.download_worker.finished_signal.connect(self.on_download_finished)
        self.download_worker.start()

    def on_download_finished(self):
        self.download_button.setEnabled(True)
        self.scan_button.setEnabled(True)
        # Refresh the all stocks tab in case the universe was updated
        self.load_all_stocks()

    def start_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            self.log_message("A scan is already running.")
            return

        self.tabs.setCurrentIndex(2) # Show logs during scan prep
        self.scan_button.setEnabled(False)
        self.download_button.setEnabled(False)

        self.scan_worker = ScannerWorker()
        self.scan_worker.log_signal.connect(self.log_message)
        self.scan_worker.finished_signal.connect(self.on_scan_finished)
        self.scan_worker.start()

    def on_scan_finished(self, results):
        self.scan_button.setEnabled(True)
        self.download_button.setEnabled(True)

        # Populate table
        self.results_table.setRowCount(0) # Clear existing
        for i, row in enumerate(results):
            self.results_table.insertRow(i)
            self.results_table.setItem(i, 0, QTableWidgetItem(str(row['symbol'])))
            self.results_table.setItem(i, 1, QTableWidgetItem(str(row['close_price'])))
            self.results_table.setItem(i, 2, QTableWidgetItem(str(row['scanners'])))

            score_item = QTableWidgetItem(str(row['score']))
            if row['score'] >= 75:
                score_item.setForeground(Qt.GlobalColor.green)
            elif row['score'] < 60:
                score_item.setForeground(Qt.GlobalColor.red)
            self.results_table.setItem(i, 3, score_item)

            self.results_table.setItem(i, 4, QTableWidgetItem(str(row['grade'])))
            self.results_table.setItem(i, 5, QTableWidgetItem(f"{row['rvol']}x"))
            self.results_table.setItem(i, 6, QTableWidgetItem(f"{row['delivery']}%"))

        self.tabs.setCurrentIndex(1) # Auto-switch to results tab
        self.log_message(f"Populated UI with {len(results)} results.")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
