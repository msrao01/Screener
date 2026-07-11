import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.db.database import init_db

def main():
    # Ensure database is initialized before launching the app
    init_db()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
