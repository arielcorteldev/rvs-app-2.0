import os
import re
import subprocess
import sys
import pymupdf  
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QDate, QSize, QUrl
from PySide6.QtGui import QPixmap, QImage, QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from utilities.stylesheets import button_style, date_picker_style, combo_box_style, message_box_style
from utilities.pdfviewer import PDFViewer
from utilities.audit_logger import AuditLogger
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from utilities.db_config import POSTGRES_CONFIG


class BookViewerWindow(QMainWindow):
    """Book Viewer Window for browsing through PDF files in a folder."""
    
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.current_user = username
        self.connection = None
        
        self.setWindowTitle("Book Viewer")
        self.setGeometry(100, 100, 1600, 1000)  # Larger window for landscape files

        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setWindowIcon(QIcon("assets/icons/application.png"))
        
        # Initialize variables
        self.current_folder = ""
        self.pdf_files = []
        self.current_index = 0
        self.default_directory = r"\\server\REGISTRY BOOKS"
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
        """)
        
        # Top control panel with fixed positioning
        control_panel = QHBoxLayout()
        control_panel.setContentsMargins(10, 10, 10, 10)
        control_panel.setSpacing(5)  # Reduced spacing between buttons
        
        # File selection button (fixed width)
        self.file_btn = QPushButton("Select File")
        self.file_btn.setStyleSheet(button_style)
        self.file_btn.setFixedWidth(120)
        self.file_btn.clicked.connect(self.select_file)
        control_panel.addWidget(self.file_btn)
        
        # Current file label (fixed width)
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("QLabel { color: #212121; font-weight: bold; }")
        self.file_label.setFixedWidth(600)
        self.file_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        control_panel.addWidget(self.file_label)
        
        # Navigation buttons (fixed width)
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.setStyleSheet(button_style)
        self.prev_btn.setFixedWidth(80)
        self.prev_btn.clicked.connect(self.previous_file)
        self.prev_btn.setEnabled(False)
        control_panel.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.setStyleSheet(button_style)
        self.next_btn.setFixedWidth(80)
        self.next_btn.clicked.connect(self.next_file)
        self.next_btn.setEnabled(False)
        control_panel.addWidget(self.next_btn)
        
        # File counter label (fixed width)
        self.counter_label = QLabel("0 / 0")
        self.counter_label.setStyleSheet("QLabel { color: #212121; font-weight: bold; }")
        self.counter_label.setFixedWidth(60)
        self.counter_label.setAlignment(Qt.AlignCenter)
        control_panel.addWidget(self.counter_label)
        
        # Zoom controls (fixed width)
        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet("QLabel { color: #212121; font-weight: bold; }")
        zoom_label.setFixedWidth(40)
        zoom_label.setAlignment(Qt.AlignCenter)
        control_panel.addWidget(zoom_label)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setStyleSheet(button_style)
        self.zoom_in_btn.setFixedSize(30, 30)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        control_panel.addWidget(self.zoom_in_btn)
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setStyleSheet(button_style)
        self.zoom_out_btn.setFixedSize(30, 30)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        control_panel.addWidget(self.zoom_out_btn)
        
        # Add stretch to push controls to the left
        control_panel.addStretch()
        
        main_layout.addLayout(control_panel)
        
        # PDF Viewer (takes full width)
        self.pdf_viewer = PDFViewer(default_zoom=1.5)
        main_layout.addWidget(self.pdf_viewer)
        
        # Status bar
        self.statusBar().showMessage("Ready")

    def create_connection(self):
        """Create and return a database connection for audit logging."""
        try:
            if self.connection is None:
                self.connection = psycopg2.connect(**POSTGRES_CONFIG)
                self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            return self.connection
        except psycopg2.Error as e:
            print(f"Error connecting to database: {str(e)}")
            return None

    def closeConnection(self):
        """Close the database connection."""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass  # Ignore close errors
            self.connection = None
        
    def select_file(self):
        """Open file dialog to select a specific PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF File",
            self.default_directory,
            "PDF Files (*.pdf)"
        )
        if file_path:
            folder_path = os.path.dirname(file_path)
            self.current_folder = folder_path
            self.load_pdf_files(selected_file=file_path)
            # Log file selection
            conn = self.create_connection()
            try:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "BOOK_VIEWER_FILE_SELECTED",
                    f"Selected file: {file_path}"
                )
                conn.commit()
            except Exception as e:
                print(f"Failed to log file selection: {e}")
            finally:
                self.closeConnection()

    def load_pdf_files(self, selected_file=None):
        """Load all PDF files from the selected folder. If selected_file is given, set current index to it."""
        try:
            self.pdf_files = []
            # Get all PDF files from the folder
            for file in os.listdir(self.current_folder):
                if file.lower().endswith('.pdf'):
                    file_path = os.path.join(self.current_folder, file)
                    self.pdf_files.append(file_path)
            # Sort files naturally (1, 2, 10 instead of 1, 10, 2)
            self.pdf_files.sort(key=lambda x: self.natural_sort_key(x))
            if self.pdf_files:
                # NOTE: `QFileDialog` may return UNC paths with `/` while `os.path.join`
                # builds paths with `\\` (or vice-versa). So we normalize both sides
                # before comparing and do it case-insensitively.
                if selected_file:
                    selected_norm = os.path.normpath(selected_file).lower()
                    normalized_to_index = {
                        os.path.normpath(p).lower(): i
                        for i, p in enumerate(self.pdf_files)
                    }
                    self.current_index = normalized_to_index.get(selected_norm, 0)
                else:
                    self.current_index = 0
                self.load_current_file()
                self.update_navigation_buttons()
                self.statusBar().showMessage(f"Loaded {len(self.pdf_files)} PDF files")
                # Log file loading
                conn = self.create_connection()
                try:
                    AuditLogger.log_action(
                        conn,
                        self.current_user,
                        "BOOK_VIEWER_FILES_LOADED",
                        f"Loaded {len(self.pdf_files)} PDF files from folder"
                    )
                    conn.commit()
                except Exception as e:
                    print(f"Failed to log files loaded: {e}")
                finally:
                    self.closeConnection()
            else:
                self.file_label.setText("No PDF files found in selected folder")
                self.counter_label.setText("0 / 0")
                self.pdf_viewer.clear_pdf()
                self.statusBar().showMessage("No PDF files found in the selected folder")
                # Log no files found
                conn = self.create_connection()
                try:
                    AuditLogger.log_action(
                        conn,
                        self.current_user,
                        "BOOK_VIEWER_NO_FILES",
                        "No PDF files found in selected folder"
                    )
                    conn.commit()
                except Exception as e:
                    print(f"Failed to log no files found: {e}")
                finally:
                    self.closeConnection()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading PDF files: {str(e)}")
            self.statusBar().showMessage("Error loading PDF files")
            
    def natural_sort_key(self, file_path):
        """Generate a key for natural sorting of filenames."""
        filename = os.path.basename(file_path)
        return [int(text) if text.isdigit() else text.lower() 
                for text in re.split('([0-9]+)', filename)]
    
    def load_current_file(self):
        """Load the current PDF file into the viewer."""
        if 0 <= self.current_index < len(self.pdf_files):
            current_file = self.pdf_files[self.current_index]
            self.pdf_viewer.load_pdf(current_file)
            
            # Update labels
            filename = os.path.basename(current_file)
            self.file_label.setText(f"Current: {filename}")
            self.counter_label.setText(f"{self.current_index + 1} / {len(self.pdf_files)}")
            
            self.statusBar().showMessage(f"Loaded: {filename}")
        else:
            self.file_label.setText("No file selected")
            self.counter_label.setText("0 / 0")
            self.pdf_viewer.clear_pdf()
            
    def next_file(self):
        """Navigate to the next PDF file."""
        if self.current_index < len(self.pdf_files) - 1:
            self.current_index += 1
            self.load_current_file()
            self.update_navigation_buttons()
            
            # Log navigation
            conn = self.create_connection()
            try:
                current_file = os.path.basename(self.pdf_files[self.current_index])
                AuditLogger.log_action(
                    conn, 
                    self.current_user, 
                    "BOOK_VIEWER_NEXT_FILE", 
                    f"Navigated to: {current_file} (Index: {self.current_index + 1}/{len(self.pdf_files)})"
                )
                conn.commit()
            except Exception as e:
                print(f"Failed to log next file navigation: {e}")
            finally:
                self.closeConnection()
            
    def previous_file(self):
        """Navigate to the previous PDF file."""
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_file()
            self.update_navigation_buttons()
            
            # Log navigation
            conn = self.create_connection()
            try:
                current_file = os.path.basename(self.pdf_files[self.current_index])
                AuditLogger.log_action(
                    conn, 
                    self.current_user, 
                    "BOOK_VIEWER_PREVIOUS_FILE", 
                    f"Navigated to: {current_file} (Index: {self.current_index + 1}/{len(self.pdf_files)})"
                )
                conn.commit()
            except Exception as e:
                print(f"Failed to log previous file navigation: {e}")
            finally:
                self.closeConnection()
            
    def update_navigation_buttons(self):
        """Update the enabled state of navigation buttons."""
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.pdf_files) - 1)
        
    def zoom_in(self):
        """Increase zoom level."""
        current_zoom = self.pdf_viewer.zoom_factor
        new_zoom = min(current_zoom * 1.2, 3.0)  # Max 300% zoom
        self.pdf_viewer.set_zoom(new_zoom)
        
        # Log zoom action
        conn = self.create_connection()
        try:
            current_file = os.path.basename(self.pdf_files[self.current_index]) if self.pdf_files else "No file"
            AuditLogger.log_action(
                conn, 
                self.current_user, 
                "BOOK_VIEWER_ZOOM_IN", 
                f"Zoomed in to {new_zoom:.2f}x on file: {current_file}"
            )
            conn.commit()
        except Exception as e:
            print(f"Failed to log zoom in action: {e}")
        finally:
            self.closeConnection()
        
    def zoom_out(self):
        """Decrease zoom level."""
        current_zoom = self.pdf_viewer.zoom_factor
        new_zoom = max(current_zoom / 1.2, 0.3)  # Min 30% zoom
        self.pdf_viewer.set_zoom(new_zoom)
        
        # Log zoom action
        conn = self.create_connection()
        try:
            current_file = os.path.basename(self.pdf_files[self.current_index]) if self.pdf_files else "No file"
            AuditLogger.log_action(
                conn, 
                self.current_user, 
                "BOOK_VIEWER_ZOOM_OUT", 
                f"Zoomed out to {new_zoom:.2f}x on file: {current_file}"
            )
            conn.commit()
        except Exception as e:
            print(f"Failed to log zoom out action: {e}")
        finally:
            self.closeConnection()
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_Left or event.key() == Qt.Key_Up:
            self.previous_file()
        elif event.key() == Qt.Key_Right or event.key() == Qt.Key_Down:
            self.next_file()
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.zoom_in()
        elif event.key() == Qt.Key_Minus:
            self.zoom_out()
        else:
            super().keyPressEvent(event)


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = BookViewerWindow()
#     window.show()
#     sys.exit(app.exec())

