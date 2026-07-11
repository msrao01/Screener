import sys
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QTextEdit, QHBoxLayout
)
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

        # Control Panel
        self.control_layout = QHBoxLayout()
        self.download_button = QPushButton("Run EOD Data Download (Kite API)")
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

        self.log_message("Application Initialized. Ready to connect to Kite API.")

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

        self.worker = DataDownloadWorker()
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
