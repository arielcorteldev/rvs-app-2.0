# IMPORT PYSIDE6 MODULES
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
import psycopg2
from utilities.db_config import POSTGRES_CONFIG
from datetime import datetime
from controllers.everify_form import eVerifyForm
from utilities.audit_logger import AuditLogger
from flask_server.app import get_access_token
from utilities.stylesheets import *
from utilities.document_types import DOCUMENT_TYPES


class ReleaseDocumentWindow(QMainWindow):
    def __init__(self, username, parent=None, main_window=None):
        super().__init__(parent)
        self.setWindowTitle("Release Document")
        self.setMinimumSize(400, 300)
        self.icon = QIcon('assets/icons/handover.png')
        self.current_user = username
        self.main_window = main_window
        
        # Set window icon
        self.icon = QIcon('assets/icons/handover.png')
        self.setWindowIcon(self.icon)
        
        # Set the style
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
            QLabel {
                font-weight: bold;
                color: #212121;
                margin-bottom: 2px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #D1D0D0;
                border-radius: 4px;
                background-color: #FFFFFF;
                margin-bottom: 10px;
                color: #212121;
            }
            QLineEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
            QPushButton {
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                color: #FFFFFF;
                margin-top: 5px;
            }
            QPushButton#release {
                background-color: #ce305e;
                color: #FFFFFF;
            }
            QPushButton#release:hover {
                background-color: #e0446a;
                color: #FFFFFF;
            }
        """)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(5)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title
        title = QLabel("Release Document")
        title.setStyleSheet("font-size: 18px; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Document Owner
        layout.addWidget(QLabel("Document Owner:"))
        self.doc_owner = QLineEdit()
        self.doc_owner.setPlaceholderText("Enter document owner")
        layout.addWidget(self.doc_owner)
        
        # Document Type
        layout.addWidget(QLabel("Type of Document:"))
        self.doc_type = QComboBox()
        self.doc_type.addItem("Select document type")
        self.doc_type.model().item(0).setEnabled(False)  # Disable the first item
        self.doc_type.addItems(DOCUMENT_TYPES)
        self.doc_type.setStyleSheet(combo_box_style)
        layout.addWidget(self.doc_type)
        
        # Number of Copies
        layout.addWidget(QLabel("Number of Copies:"))
        self.copy_no = QLineEdit()
        self.copy_no.setPlaceholderText("Enter number of copies")
        # Only allow integers
        self.copy_no.setValidator(QIntValidator(1, 999))
        layout.addWidget(self.copy_no)
        
        # Received By
        layout.addWidget(QLabel("Received By:"))
        self.received_by = QLineEdit()
        self.received_by.setPlaceholderText("Verify receiver using eVerify or manually input")
        layout.addWidget(self.received_by)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Release Button
        self.release_btn = QPushButton("Release Document")
        self.release_btn.setObjectName("release")
        self.release_btn.clicked.connect(self.release_document)
        button_layout.addWidget(self.release_btn)
        
        # eVERIFY Button
        self.everify_btn = QPushButton()
        self.everify_btn.setIcon(QIcon("assets/icons/everify-icon.png"))
        self.everify_btn.setIconSize(QSize(130, 40))
        self.everify_btn.setStyleSheet(everify_button_style)
        self.everify_btn.setToolTip("Launch eVerify Authentication")
        self.everify_btn.clicked.connect(self.start_everify_flow)
        button_layout.addWidget(self.everify_btn)

        # self.everify_form = eVerifyForm(self.current_user)
        # self.everify_form.fullNameVerified.connect(self.populate_received_by_field)
        
        layout.addLayout(button_layout)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
    def create_connection(self):
        """Create a database connection"""
        try:
            conn = psycopg2.connect(**POSTGRES_CONFIG)
            return conn
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Database Error", 
                               f"Could not connect to database: {str(e)}")
            return None

    def closeConnection(self, conn=None):
        """Safely close the database connection"""
        if conn:
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing connection: {str(e)}")
            
    def release_document(self):
        """Handle document release"""
        # Validate inputs
        if not all([self.doc_owner.text(), self.doc_type.currentIndex() > 0, 
                   self.copy_no.text(), self.received_by.text()]):
            conn = self.create_connection()
            try:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "RELEASE_VALIDATION_FAILED",
                    {"error": "Missing required fields"}
                )
                conn.commit()
            finally:
                self.closeConnection(conn)
            
            QMessageBox.warning(self, "Input Error", 
                              "All fields are required!")
            return
            
        conn = None
        try:
            conn = self.create_connection()
            if not conn:
                return

            cursor = conn.cursor()
            
            # Log the release attempt
            AuditLogger.log_action(
                conn,
                self.current_user,
                "DOCUMENT_RELEASE_INITIATED",
                {
                    "doc_owner": self.doc_owner.text().strip(),
                    "doc_type": self.doc_type.currentText(),
                    "copy_no": self.copy_no.text(),
                    "received_by": self.received_by.text().strip()
                }
            )

            cursor.execute("""
                SELECT firstname, lastname
                FROM users_list
                WHERE username = %s
                """, (
                    self.current_user,
                ))
            
            result = cursor.fetchone()
            user_name = f"{result[0]} {result[1]}"
            
            # Insert into releasing_log
            cursor.execute("""
                INSERT INTO releasing_log 
                (doc_owner, doc_type, copy_no, received_by, released_by)
                VALUES (%s, %s, %s, %s, %s)
                """, (
                    self.doc_owner.text().strip(),
                    self.doc_type.currentText(),
                    int(self.copy_no.text()),
                    self.received_by.text().strip(),
                    user_name
                ))
            
            # Log successful release
            AuditLogger.log_action(
                conn,
                self.current_user,
                "DOCUMENT_RELEASE_SUCCESS",
                {"message": "Document successfully released"}
            )
            
            conn.commit()
            
            QMessageBox.information(self, "Success", 
                                  "Document released successfully!")
            
            # Clear the form
            self.clear_form()
            
        except psycopg2.Error as e:
            if conn:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "DOCUMENT_RELEASE_ERROR",
                    {"error": str(e)}
                )
                conn.commit()
            QMessageBox.critical(self, "Database Error", 
                               f"Error releasing document: {str(e)}")
        finally:
            self.closeConnection(conn)
    
    def clear_form(self):
        """Clear all form fields"""
        self.doc_owner.clear()
        self.doc_type.setCurrentIndex(0)
        self.copy_no.clear()
        self.received_by.clear()

    def start_everify_flow(self):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(conn, self.current_user, "EVERIFY_INITIATED")
            conn.commit()
            # Get the access token using backend function
            access_token = get_access_token()  # This handles refresh and token logic

            if access_token:
                print("✅ Token successfully acquired and valid.")
                everify = self.main_window.get_everify_form()
                everify.fullNameVerified.connect(self.populate_received_by_field)
                everify.show()
                everify.raise_()
                everify.activateWindow()

            else:
                print("❌ Failed to acquire a token.")
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "EVERIFY_TOKEN_ERROR",
                    {"error": "Failed to acquire token"}
                )
                conn.commit()
        finally:
            self.closeConnection()
    
    
    def populate_received_by_field(self, full_name):
        """Populate the received by field with the verified full name"""
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "RECEIVED_BY_FIELD_POPULATED",
                {"full_name": full_name}
            )
            conn.commit()
            
            self.show_release_window()
            
            self.received_by.setText(full_name)
            print(f"🔍 Auto-filled received_by with: {full_name}")
        finally:
            self.closeConnection(conn)

    def show_release_window(self):
        """Bring this window to front and activate it."""
        # If it's minimized, restore it
        if self.isMinimized():
            self.showNormal()
        # Show it (if it was hidden)
        self.show()
        # Raise it above other windows
        self.raise_()
        # Give it focus
        self.activateWindow()

    def closeEvent(self, event):
        """Handle window close event"""
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "RELEASE_WINDOW_CLOSED",
                {"message": "Release Document window closed"}
            )
            conn.commit()
        finally:
            self.closeConnection(conn)
            event.ignore()
            self.hide()

# if __name__ == "__main__":
#     from PySide6.QtWidgets import QApplication
#     import sys
    
#     app = QApplication(sys.argv)
#     window = ReleaseDocumentWindow("test_user")  # For testing purposes
#     window.show()
#     sys.exit(app.exec()) 