import sys
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QTextEdit, QHBoxLayout,
    QComboBox, QFormLayout, QLineEdit, QGroupBox
)
import os
from dotenv import set_key
from PySide6.QtCore import Qt
from src.services.data_service import DataDownloadWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.download_button = QPushButton("SYNC UNIVERSE && DOWNLOAD DATA")
        self.download_button.setMinimumHeight(50)
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:disabled { background-color: #7f8c8d; color: #bdc3c7; }
        """)
        self.download_button.clicked.connect(self.start_download)
        self.left_layout.addWidget(self.download_button)

        self.main_layout.addWidget(self.left_panel)

        # Right Panel (Status/Log Area)
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)

        self.log_label = QLabel("Execution Logs")
        self.log_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #bdc3c7;")
        self.right_layout.addWidget(self.log_label)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ecf0f1;
                font-family: Consolas, monospace;
                font-size: 12px;
                border: 1px solid #34495e;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        self.right_layout.addWidget(self.log_area)
        self.main_layout.addWidget(self.right_panel)

        self.worker = None

        self.log_message("Application Initialized.")
        self.log_message("Select your broker on the left and click Sync Universe to begin.")

    def apply_dark_theme(self):
        """Applies a global dark theme to the application."""
        self.setStyleSheet("""
            QMainWindow { background-color: #2c3e50; }
            QWidget { color: #ecf0f1; font-family: 'Segoe UI', Arial, sans-serif; }
            QGroupBox {
                border: 1px solid #34495e;
                border-radius: 6px;
                margin-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }
            QLineEdit, QComboBox {
                background-color: #34495e;
                border: 1px solid #2c3e50;
                border-radius: 3px;
                padding: 5px;
                color: #ecf0f1;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #3498db; }
            QPushButton {
                background-color: #2980b9;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3498db; }
            QPushButton:pressed { background-color: #2471a3; }
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

    def log_message(self, message):
        """Appends a message to the status area."""
        self.log_area.append(message)
        logger.info(message)

    def start_download(self):
        if self.worker and self.worker.isRunning():
            self.log_message("A download process is already running.")
            return

        self.download_button.setEnabled(False)
        self.log_area.clear()

        broker_type = self.broker_combo.currentText()
        self.worker = DataDownloadWorker(broker_type=broker_type)
        self.worker.log_signal.connect(self.log_message)
        self.worker.finished_signal.connect(self.on_download_finished)
        self.worker.start()

    def on_download_finished(self):
        self.download_button.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
