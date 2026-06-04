from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTableWidget, QTableWidgetItem, QLabel, QLineEdit, 
                            QPushButton, QDateTimeEdit, QComboBox, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QFont, QColor, QIcon
import psycopg2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, portrait
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from utilities.db_config import POSTGRES_CONFIG
from datetime import datetime, date, timedelta
from utilities.audit_logger import AuditLogger
from utilities.stylesheets import message_box_style, table_style, date_picker_style, combo_box_style

folio = (8.5 * inch, 13 * inch)

class ComelecDeathReportWindow(QMainWindow):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle("COMELEC Death Report")
        self.setMinimumSize(1200, 600)
        self.current_user = username
        
        # Set window icon
        self.icon = QIcon('assets/icons/grave.png')
        self.setWindowIcon(self.icon)
        
        # Set the style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
            QLabel {
                font-weight: bold;
                color: #212121;
            }
            QLineEdit, QComboBox, QDateTimeEdit {
                padding: 5px;
                border: 1px solid #D1D0D0;
                border-radius: 4px;
                background-color: #FFFFFF;
                color: #212121;
            }
            QLineEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
            QComboBox:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                color: #FFFFFF;
            }
            QPushButton#filter {
                background-color: #ce305e;
            }
            QPushButton#filter:hover {
                background-color: #e0446a;
            }
            QPushButton#reset {
                background-color: #ce305e;
            }
            QPushButton#reset:hover {
                background-color: #e0446a;
            }
        """)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 8, 10, 10)
        
        # Create filter section
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(5)
        
        # Date range filter
        date_range_layout = QHBoxLayout()
        date_range_layout.setSpacing(3)
        date_range_layout.setContentsMargins(0, 0, 0, 0)
        
        self.start_date = QDateTimeEdit()
        self.start_date.setDateTime(QDateTime.currentDateTime().addDays(-7))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("MM/dd/yyyy")
        self.start_date.setFixedWidth(145)
        self.start_date.setStyleSheet(date_picker_style)

        self.end_date = QDateTimeEdit()
        self.end_date.setDateTime(QDateTime.currentDateTime())
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("MM/dd/yyyy")
        self.end_date.setFixedWidth(145)
        self.end_date.setStyleSheet(date_picker_style)

        date_range_layout.addWidget(self.start_date)
        date_range_layout.addWidget(QLabel("to"))
        date_range_layout.addWidget(self.end_date)
        date_range_layout.addStretch()
        filter_layout.addLayout(date_range_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(3)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Filter button
        self.filter_button = QPushButton("Apply Filters")
        self.filter_button.setObjectName("filter")
        self.filter_button.clicked.connect(self.apply_filters)
        button_layout.addWidget(self.filter_button)
        
        # Reset button
        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("reset")
        self.reset_button.clicked.connect(self.reset_filters)
        button_layout.addWidget(self.reset_button)

        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("filter")  # Use same style as filter button
        self.refresh_button.clicked.connect(self.load_data)
        button_layout.addWidget(self.refresh_button)

        # Export PDF button
        self.export_pdf_button = QPushButton("Export PDF")
        self.export_pdf_button.setObjectName("filter")  # Use same style as filter button
        self.export_pdf_button.clicked.connect(self.export_pdf)
        button_layout.addWidget(self.export_pdf_button)
        
        button_layout.addStretch()
        
        filter_layout.addLayout(button_layout)
        layout.addLayout(filter_layout)
        
        # Add minimal spacing before the table
        layout.addSpacing(3)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Name of Deceased", "Address", "Date of Birth", "Date of Death"
        ])
        # self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(table_style)
        layout.addWidget(self.table)
        
        # Load initial data
        # self.load_document_types()
        self.load_data()
        
    def create_connection(self):
        """Create a new PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(**POSTGRES_CONFIG)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except psycopg2.Error as e:
            print(f"Error creating connection: {str(e)}")
            return None

    def closeConnection(self, conn=None):
        """Safely close the database connection"""
        if conn:
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing connection: {str(e)}")

    def load_data(self):
        """Load releasing log data with current filters"""
        conn = self.create_connection()
        if not conn:
            print("Failed to connect to database")
            return
        try:
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT name, residence, date_of_birth, date_of_death
                FROM death_index 
                WHERE age_years >= 18
                AND residence ILIKE %s
                AND date_of_reg BETWEEN %s AND %s
            """
            params = ['%maasin%']
            filter_details = {}
            
            start_date = self.start_date.dateTime().toPython()
            end_date = self.end_date.dateTime().toPython()
            params.extend([start_date, end_date])
            filter_details.update({
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            })
            

            
            # Order by registration date asc
            query += " ORDER BY date_of_reg ASC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Log the data load
            AuditLogger.log_action(
                conn,
                self.current_user,
                "COMELEC_REPORT_LOADED",
                {
                    "filters": filter_details,
                    "rows_returned": len(rows)
                }
            )
            conn.commit()
            
            # Update table
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                # Only populate the first 4 columns (name, residence, date_of_birth, date_of_death)
                for j in range(min(len(row), self.table.columnCount())):
                    value = row[j]
                    if isinstance(value, (datetime, date)):
                        value = value.strftime("%B %#d, %Y")
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Make cell read-only
                    self.table.setItem(i, j, item)
            
            # Adjust column widths
            self.table.resizeColumnsToContents()
            
        except psycopg2.Error as e:
            print(f"Error loading data: {str(e)}")
            if conn:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "COMELEC_REPORT_LOAD_ERROR",
                    {"error": str(e)}
                )
                conn.commit()
        finally:
            self.closeConnection(conn)
    
    def apply_filters(self):
        """Apply the current filters and reload data"""
        conn = self.create_connection()
        if not conn:
            print("Failed to connect to database")
            return
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "COMELEC_REPORT_FILTERS_APPLIED",
                {
                    "start_date": self.start_date.dateTime().toPython().isoformat(),
                    "end_date": self.end_date.dateTime().toPython().isoformat()
                }
            )
            conn.commit()
        finally:
            self.closeConnection(conn)
            
        self.load_data()
    
    def reset_filters(self):
        """Reset all filters to default values"""
        conn = self.create_connection()
        if not conn:
            print("Failed to connect to database")
            return
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "COMELEC_REPORT_FILTERS_RESET",
                {"message": "All filters reset to default values"}
            )
            conn.commit()
        finally:
            self.closeConnection(conn)
            
        self.start_date.setDateTime(QDateTime.currentDateTime().addDays(-7))
        self.end_date.setDateTime(QDateTime.currentDateTime())
        self.load_data()

    def draw_wrapped_text(self, canvas, text, x, y, max_width, line_height=10, font_name="Helvetica", font_size=8):
        words = text.split()
        line = ""
        lines = []

        for word in words:
            test_line = line + word + " "
            if pdfmetrics.stringWidth(test_line, font_name, font_size) <= max_width:
                line = test_line
            else:
                lines.append(line.strip())
                line = word + " "
        if line:
            lines.append(line.strip())

        for line in lines:
            canvas.drawString(x, y, line)
            y -= line_height

        return y

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "ComelecDeathReport.pdf", "PDF files (*.pdf)")
        if not path:
            return

        try:
            c = canvas.Canvas(path, pagesize=portrait(folio))
            width, height = portrait(folio)
            margin = 40
            y = height - margin
            
            # --- 1. Header & Branding Section ---
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width / 2, y - 10, "REGISTERED DEATH")
            
            # Add subtitle with month and year
            end_date_obj = self.end_date.dateTime().toPython()
            month_year = end_date_obj.strftime("%B %Y")
            c.setFont("Helvetica", 11)
            c.drawCentredString(width / 2, y - 25, f"For the month of {month_year}")

            y -= 45
            
            # --- 2. Table Configuration ---
            # Order: ID, Owner, Type, Copy, Received, Released, Timestamp
            col_widths = [160, 160, 100, 100] 
            total_table_width = sum(col_widths)
            
            col_offsets = []
            curr_x = margin
            for w in col_widths:
                col_offsets.append(curr_x)
                curr_x += w

            # --- 3. Draw Table Header ---
            c.setFont("Helvetica-Bold", 9)
            header_height = 20
            c.setFillColorRGB(0.85, 0.85, 0.85) # Gray header background
            c.rect(margin, y - header_height, total_table_width, header_height, stroke=1, fill=1)
            c.setFillColorRGB(0, 0, 0)

            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            for i, header in enumerate(headers):
                c.drawString(col_offsets[i] + 5, y - 14, header)
                c.line(col_offsets[i], y, col_offsets[i], y - header_height)
            c.line(margin + total_table_width, y, margin + total_table_width, y - header_height)
            
            y -= header_height

            # --- 4. Data Rows with Striping & Borders ---
            c.setFont("Helvetica", 8)
            for row in range(self.table.rowCount()):
                # Calculate height needed
                row_max_lines = 1
                for col in [0, 1]:
                    text = self.table.item(row, col).text() if self.table.item(row, col) else ""
                    text_width = pdfmetrics.stringWidth(text, "Helvetica", 8)
                    lines = int(text_width / (col_widths[col] - 10)) + 1
                    row_max_lines = max(row_max_lines, lines)
                
                row_height = max(20, row_max_lines * 10 + 5)

                if y - row_height < 60:
                    c.showPage()
                    y = height - margin
                    c.setFont("Helvetica", 8)

                # Zebra Striping
                if row % 2 == 1:
                    c.setFillColorRGB(0.96, 0.96, 0.96)
                    c.rect(margin, y - row_height, total_table_width, row_height, stroke=0, fill=1)
                    c.setFillColorRGB(0, 0, 0)

                # Draw Text
                start_y = y
                for col in range(self.table.columnCount()):
                    text = self.table.item(row, col).text() if self.table.item(row, col) else ""
                    if col in [0, 1]: 
                        self.draw_wrapped_text(c, text, col_offsets[col] + 5, y - 10, col_widths[col] - 10)
                    else:
                        c.drawString(col_offsets[col] + 5, y - 12, text)

                # Grid Lines
                for x_pos in col_offsets:
                    c.line(x_pos, y, x_pos, y - row_height)
                c.line(margin + total_table_width, y, margin + total_table_width, y - row_height)
                y -= row_height
                c.line(margin, y, margin + total_table_width, y)

            # --- 5. Summary Section ---
            y -= 30
            if y < 60:
                c.showPage()
                y = height - margin
            
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin, y, f"TOTAL NUMBER OF DEATH REPORTS: {self.table.rowCount()}")
            
            # Add signature block below total count
            y -= 40
            c.setFont("Helvetica-Bold", 10)
            x_pos = width - margin - 150
            c.drawString(x_pos, y, "JENNY F. ANG")
            
            # Draw underline under the name
            name_width = pdfmetrics.stringWidth("JENNY F. ANG", "Helvetica-Bold", 10)
            c.line(x_pos, y - 2, x_pos + name_width, y - 2)
            
            c.setFont("Helvetica", 9)
            c.drawString(x_pos, y - 12, "City Civil Registrar")

            c.save()
            box = QMessageBox()
            box.setIcon(QMessageBox.Information)
            box.setText(f"PDF saved to:\n{path}")
            box.setWindowTitle("Export Successful")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()

        except Exception as e:
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setText(f"An error occurred:\n{str(e)}")
            box.setWindowTitle("Export Failed")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()

    def closeEvent(self, event):
        """Handle window close event"""
        conn = self.create_connection()
        if not conn:
            event.ignore()
            self.hide()
            return
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "RELEASE_VIEWER_CLOSED",
                {"message": "Document Release Log Viewer window closed"}
            )
            conn.commit()
        finally:
            self.closeConnection(conn)
            event.ignore()
            self.hide()