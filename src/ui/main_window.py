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
        self.setWindowTitle("NSE Smart Money Scanner - V1 Foundation")
        self.resize(800, 600)

        # Main Widget and Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Header
        self.header_label = QLabel("Scanner Dashboard")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        self.layout.addWidget(self.header_label)

        # Broker Settings Group
        self.broker_group = QGroupBox("Broker Login & Settings")
        self.broker_layout = QFormLayout()

        self.broker_combo = QComboBox()
        self.broker_combo.addItems(["Zerodha Kite", "Upstox"])
        self.broker_combo.currentTextChanged.connect(self.on_broker_changed)
        self.broker_layout.addRow("Select Broker:", self.broker_combo)

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
        self.layout.addWidget(self.broker_group)

        # Load initial credentials
        self.on_broker_changed(self.broker_combo.currentText())

        # Control Panel
        self.control_layout = QHBoxLayout()
        self.download_button = QPushButton("Run EOD Data Download")
        self.download_button.setMinimumHeight(40)
        self.download_button.setStyleSheet("font-size: 14px;")

        self.control_layout.addStretch()
        self.control_layout.addWidget(self.download_button)
        self.control_layout.addStretch()
        self.layout.addLayout(self.control_layout)

        self.download_button.clicked.connect(self.start_download)

        # Status/Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #f0f0f0; font-family: monospace;")
        self.layout.addWidget(self.log_area)

        self.worker = None

        self.log_message("Application Initialized. Select broker and save credentials to begin.")

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
