from PySide6.QtWidgets import QMainWindow, QWidget, QPushButton, QVBoxLayout, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
import sys
from utilities.stylesheets import button_style
from controllers.tagging_birth import BirthTaggingWindow
from controllers.tagging_death import DeathTaggingWindow
from controllers.tagging_marriage import MarriageTaggingWindow
from utilities.audit_logger import AuditLogger
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from utilities.db_config import POSTGRES_CONFIG

class TaggingMainWindow(QMainWindow):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.current_user = username
        self.setWindowTitle("Tagging Tool")
        self.setFixedSize(300, 200)

        self.setWindowIcon(QIcon("assets/icons/application.png"))

        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
        """)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        central_widget.setLayout(layout)

        # Buttons
        self.live_birth_button = QPushButton("Live Birth")
        self.death_button = QPushButton("Death")
        self.marriage_button = QPushButton("Marriage")

        for btn in [self.live_birth_button, self.death_button, self.marriage_button]:
            btn.setFixedHeight(40)
            btn.setFixedWidth(250)
            btn.setStyleSheet(button_style)
            layout.addWidget(btn)

        # Connect signals (optional)
        self.live_birth_button.clicked.connect(self.open_birth_tagging)
        self.death_button.clicked.connect(self.open_death_tagging)
        self.marriage_button.clicked.connect(self.open_marriage_tagging)


    def create_connection(self):
        """Create a new database connection"""
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn

    def closeConnection(self):
        """Close the database connection"""
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()
            self.connection = None

    # Slot methods
    def open_birth_tagging(self):
        conn = self.create_connection()
        try:
            self.birth_window = BirthTaggingWindow(self.current_user, parent=self)
            self.birth_window.showMaximized()
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "BirthTaggingWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def open_death_tagging(self):
        conn = self.create_connection()
        try:
            self.death_window = DeathTaggingWindow(self.current_user, parent=self)
            self.death_window.showMaximized()
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "DeathTaggingWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def open_marriage_tagging(self):
        conn = self.create_connection()
        try:
            self.marriage_window = MarriageTaggingWindow(self.current_user, parent=self)
            self.marriage_window.showMaximized()
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "MarriageTaggingWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def closeEvent(self, event):
        """Handle window close event"""
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_CLOSED",
                {"window": "TaggingWindow"}
            )
        finally:
            self.closeConnection()
        event.accept()

# Run this standalone
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TaggingMainWindow()
    window.show()
    sys.exit(app.exec())
