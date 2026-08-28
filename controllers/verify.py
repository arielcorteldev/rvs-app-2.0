import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import requests
import webbrowser
import subprocess
from flask_server.app import get_access_token
from controllers.everify_form import eVerifyForm

# IMPORT PYSIDE6 MODULES
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog

# IMPORT UI 
from ui.Search_Birth_Window import Ui_SearchBirthWindow
from ui.Search_Death_Window import Ui_SearchDeathWindow
from ui.Search_Marriage_Window import Ui_SearchMarriageWindow

from utilities.audit_logger import AuditLogger
from utilities.html_renderer import render_html_form
from utilities.db_config import POSTGRES_CONFIG

from utilities.stylesheets import search_button_style, everify_button_style, button_style, message_box_style

# Base class for searching PDF records - MODIFY open_form_file method
class VerifyWindowBase(QMainWindow):
    def __init__(self, ui_class, search_path, form_file, no_record_file, destroyed_file, username, parent=None, main_window=None):
        super().__init__(parent)
        self.ui = ui_class()
        self.ui.setupUi(self)
        
        # print(f"DEBUG - VerifyWindowBase received username: {username}")
        self.current_user = username
        self.main_window = main_window
        # Get full name from main_window if available, otherwise use username as fallback
        self.current_user_full_name = getattr(main_window, 'current_user_full_name', username) if main_window else username

        # Add database connection method
        self.connection = None

        self.setFixedSize(QSize(800, 600))
        self.search_path = search_path
        self.form_file = form_file
        self.no_record_file = no_record_file
        self.destroyed_file = destroyed_file

        # Set styles
        for button in [
            self.ui.search_button, self.ui.create_form, self.ui.no_record,
            self.ui.destroyed, self.ui.auto_form
        ]:
            button.setStyleSheet(search_button_style)
        
        

        self.ui.centralwidget.setStyleSheet("background-color: #FFFFFF;")
        
        self.ui.results_list.setStyleSheet("""
            QListWidget {
                background-color: #F2F2F2;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                color: #212121;  
                padding: 5px;
            }

            QListWidget::item:selected {
                background-color: #ce305e;  
                color: #FFFFFF;
            }

            QListWidget::item:hover {
                background-color: #e0446a;  
                color: #212121;
            }
        """)

        self.ui.search_textEdit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
        """)
        self.ui.regyear_textEdit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
        """)
        self.ui.search_by_comboBox.setFixedWidth(100)
        self.ui.search_by_comboBox.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox::item {
                background-color: #FFFFFF;
                color: #212121;
            }
            QComboBox::item:hover {
                background-color: #ce305e;
                color: #FFFFFF;
            }
            QComboBox::item:selected {
                background-color: #ce305e;
                color: #FFFFFF;
            }
            QComboBox:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
        """)
        
        # Set tooltips
        self.ui.auto_form.setToolTip("Auto-generate Form")
        self.ui.create_form.setToolTip("Create Form")
        self.ui.no_record.setToolTip("Create No Record Form")
        self.ui.destroyed.setToolTip("Create Record Destroyed Form")
        
        # Create "Add Remarks" button
        self.add_remarks_button = QPushButton()
        self.add_remarks_button.setIcon(QIcon("assets/icons/comment.png"))
        self.add_remarks_button.setIconSize(QSize(20, 20))
        self.add_remarks_button.setStyleSheet(search_button_style)
        self.add_remarks_button.setToolTip("Add remarks to selected record")
        
        # Connect buttons
        self.ui.auto_form.clicked.connect(self.open_auto_form)
        self.ui.search_button.clicked.connect(self.search_pdfs)
        self.ui.create_form.clicked.connect(self.open_form_file)
        self.ui.no_record.clicked.connect(self.open_no_record)
        self.ui.destroyed.clicked.connect(self.open_destroyed_record)
        self.add_remarks_button.clicked.connect(self.add_remarks_to_record)

        # Setup combo box
        self.ui.search_by_comboBox.addItems(["Name", "Date", "Reg No."])
        
        # List for found PDFs
        self.found_pdfs = []
        
        # Open file on double-click
        self.ui.results_list.itemDoubleClicked.connect(self.open_selected_file)

        # Add eVerify button
        self.ui.everify_button.setIcon(QIcon("assets/icons/everify-icon.png"))
        self.ui.everify_button.setIconSize(QSize(130, 40))
        self.ui.everify_button.setFixedWidth(130)
        self.ui.everify_button.setText("")
        self.ui.everify_button.setStyleSheet(everify_button_style)
        self.ui.everify_button.setToolTip("Launch eVerify Authentication")
        self.ui.everify_button.clicked.connect(self.start_everify_flow)

        # Create a new horizontal layout for the search area
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(10)

        # Add search by combo box to the layout
        search_layout.addWidget(self.ui.search_by_comboBox)
        
        # Add search text edit to the layout
        search_layout.addWidget(self.ui.search_textEdit)
        
        # Add search button to the layout
        search_layout.addWidget(self.ui.search_button)
        
        # Add spacer to push eVerify button to the right
        search_layout.addStretch()
        
        # Add eVerify button to the layout
        search_layout.addWidget(self.ui.everify_button)

        # Set fixed size policies
        self.ui.search_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.ui.everify_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.ui.search_textEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ui.search_by_comboBox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Set minimum sizes to prevent shrinking
        self.ui.search_button.setMinimumWidth(100)
        self.ui.everify_button.setMinimumWidth(130)
        self.ui.search_by_comboBox.setMinimumWidth(100)
        self.ui.search_textEdit.setMinimumWidth(200)

        # Set maximum sizes to prevent expanding
        self.ui.search_button.setMaximumWidth(100)
        self.ui.everify_button.setMaximumWidth(130)
        self.ui.search_by_comboBox.setMaximumWidth(100)

        # Add "Add Remarks" button to the vertical button layout
        # Find the vertical layout that contains the form buttons (auto_form, create_form, etc.)
        if hasattr(self.ui, 'verticalLayout'):
            self.add_remarks_button.setFixedHeight(32)
            self.ui.verticalLayout.addWidget(self.add_remarks_button)

        # Replace the old horizontal layout with the new search layout
        if self.ui.horizontalLayout.count() > 0:
            # Remove all items from the old layout
            while self.ui.horizontalLayout.count():
                item = self.ui.horizontalLayout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
                elif item.layout():
                    item.layout().setParent(None)

        # Add the new search layout to the grid layout
        self.ui.gridLayout.addLayout(search_layout, 0, 1, 1, 2)

        # Update the layout
        self.ui.gridLayout.update()
        self.updateGeometry()

    def create_connection(self):
        try:
            if self.connection is None:
                self.connection = psycopg2.connect(**POSTGRES_CONFIG)
                self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            return self.connection
        except psycopg2.Error as e:
            print(f"Error connecting to database: {str(e)}")
            return None

    def closeConnection(self):
        if self.connection:
            try:
                self.connection.close()
            except:
                pass  # Ignore close errors
            self.connection = None
    
    def normalize_path(self, path):
        """Normalize file path by converting all slashes to forward slashes."""
        return path.replace('\\', '/').replace('//', '/')

    def open_auto_form(self):
        conn = self.create_connection()
        cursor = None
        self.form_preview_window = None # Initialize to None
        try:
            # Get the selected record from results list, identified by DB row ID
            selected_items = self.ui.results_list.selectedItems()
            if not selected_items:
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Please select a record first.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            record_id = selected_items[0].data(Qt.UserRole)
            if record_id is None:
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Could not identify the selected record.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            # Get the record data from database
            cursor = conn.cursor()

            print(f"\nGenerating auto-form for record id: {record_id}")

            record_dict = {}
            form_type = ""

            # Determine which table to query based on window type and fetch data into a dictionary
            if isinstance(self, VerifyBirthWindow):
                form_type = "Birth"

                cursor.execute("""
                    SELECT name, date_of_birth, sex, page_no, book_no, reg_no, 
                           date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                           name_of_father, nationality_father, parents_marriage_date,
                           parents_marriage_place, attendant, remarks
                    FROM birth_index 
                    WHERE id = %s
                """, (record_id,))
                record = cursor.fetchone()
                if record:
                    (name, dob, sex, page_no, book_no, reg_no, dor, pob, mother, mother_nat, father, father_nat, parents_marriage_date, parents_marriage_place, attendant, remarks) = record
                    record_dict = {
                        'name': name,
                        'date_of_birth': dob.strftime('%Y-%m-%d') if dob else '',
                        'sex': sex,
                        'page_no': str(page_no) if page_no else '',
                        'book_no': str(book_no) if book_no else '',
                        'reg_no': reg_no,
                        'date_of_reg': dor.strftime('%Y-%m-%d') if dor else '',
                        'place_of_birth': pob,
                        'name_of_mother': mother,
                        'nationality_mother': mother_nat,
                        'name_of_father': father,
                        'nationality_father': father_nat,
                        'parents_marriage_date': parents_marriage_date.strftime('%Y-%m-%d') if parents_marriage_date else '',
                        'parents_marriage_place': parents_marriage_place,
                        'attendant': attendant,
                        'remarks': remarks
                    }

            elif isinstance(self, VerifyDeathWindow):
                form_type = "Death"

                cursor.execute("""
                    SELECT name, date_of_death, sex, page_no, book_no, reg_no,
                           date_of_reg, age_years, civil_status, nationality, place_of_death,
                           cause_of_death, remarks
                    FROM death_index 
                    WHERE id = %s
                """, (record_id,))
                record = cursor.fetchone()
                if record:
                    (name, dod, sex, page_no, book_no, reg_no, dor, age, civil_status, nationality, pod, cod, remarks) = record
                    record_dict = {
                        'name': name,
                        'date_of_death': dod.strftime('%Y-%m-%d') if dod else '',
                        'sex': sex,
                        'page_no': str(page_no) if page_no else '',
                        'book_no': str(book_no) if book_no else '',
                        'reg_no': reg_no,
                        'date_of_reg': dor.strftime('%Y-%m-%d') if dor else '',
                        'age': str(age) if age else '',
                        'civil_status': civil_status,
                        'nationality': nationality,
                        'place_of_death': pod,
                        'cause_of_death': cod,
                        'remarks': remarks
                    }

            elif isinstance(self, VerifyMarriageWindow):
                form_type = "Marriage"

                cursor.execute("""
                    SELECT husband_name, wife_name, date_of_marriage, page_no, book_no, reg_no,
                           husband_age, wife_age, husb_nationality, wife_nationality,
                           husb_civil_status, wife_civil_status, husb_mother, wife_mother,
                           husb_father, wife_father, date_of_reg, place_of_marriage, remarks
                    FROM marriage_index 
                    WHERE id = %s
                """, (record_id,))
                record = cursor.fetchone()
                if record:
                    (husband, wife, dom, page_no, book_no, reg_no, husband_age, wife_age, husb_nat, wife_nat, husb_civil, wife_civil, husb_mother, wife_mother, husb_father, wife_father, dor, pom, remarks) = record
                    record_dict = {
                        'husband_name': husband,
                        'wife_name': wife,
                        'date_of_marriage': dom.strftime('%Y-%m-%d') if dom else '',
                        'page_no': str(page_no) if page_no else '',
                        'book_no': str(book_no) if book_no else '',
                        'reg_no': reg_no,
                        'husband_age': str(husband_age) if husband_age else '',
                        'wife_age': str(wife_age) if wife_age else '',
                        'husb_nationality': husb_nat,
                        'wife_nationality': wife_nat,
                        'husb_civil_status': husb_civil,
                        'wife_civil_status': wife_civil,
                        'husb_mother': husb_mother,
                        'wife_mother': wife_mother,
                        'husb_father': husb_father,
                        'wife_father': wife_father,
                        'date_of_reg': dor.strftime('%Y-%m-%d') if dor else '',
                        'place_of_marriage': pom,
                        'remarks': remarks
                    }
            else:
                raise ValueError("Unknown window type for form preview")

            if not record_dict:
                print(f"No record data found for record id: {record_id}")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("No record data found for the selected record.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return
            
            # Instead of using the in-app FormPreviewWindow, render an HTML
            # preview and open it in the user's external browser.
            # `render_html_form` will return a path to a temporary HTML file.
            from datetime import date
            today = date.today().isoformat()  # Format: YYYY-MM-DD
            html_path = render_html_form(record_dict, form_type, current_user=self.current_user_full_name, today_date=today)

            # Log that an HTML preview was generated and opened.
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_HTML_PREVIEW",
                {"form_type": form_type, "path": html_path}
            )
            conn.commit()

            # Close DB resources before launching external browser.
            if cursor:
                cursor.close()
                cursor = None
            self.closeConnection()

            # Open the rendered HTML in the default external browser.
            try:
                import webbrowser
                from pathlib import Path
                webbrowser.open(Path(html_path).as_uri())
            except Exception as _open_err:
                # If opening the browser fails, show a message box but do not
                # re-open database connections here.
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText(f"Rendered form saved to: {html_path}\nFailed to open browser: {_open_err}")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()

        except Exception as e:
            print(f"Error in open_form_file: {str(e)}")
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPEN_ERROR",
                {"form_type": "UNKNOWN", "error": str(e)}
            )
            conn.commit()
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to open form: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            if cursor:
                cursor.close()
            self.closeConnection()

    def add_remarks_to_record(self):
        """Add or update remarks for the selected record in the database."""
        conn = self.create_connection()
        cursor = None
        try:
            # Get the selected file from results list
            selected_items = self.ui.results_list.selectedItems()
            if not selected_items:
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Please select a record first.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            record_id = selected_items[0].data(Qt.UserRole)
            if record_id is None:
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Could not identify the selected record.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            # Get the record data from database to identify the record
            cursor = conn.cursor()

            print(f"\nFetching reg_no for record id: {record_id}")

            reg_no = None
            table_name = None
            form_type = ""

            # Determine which table to query based on window type
            if isinstance(self, VerifyBirthWindow):
                table_name = "birth_index"
                form_type = "Birth"
                cursor.execute("SELECT reg_no FROM birth_index WHERE id = %s", (record_id,))
            elif isinstance(self, VerifyDeathWindow):
                table_name = "death_index"
                form_type = "Death"
                cursor.execute("SELECT reg_no FROM death_index WHERE id = %s", (record_id,))
            elif isinstance(self, VerifyMarriageWindow):
                table_name = "marriage_index"
                form_type = "Marriage"
                cursor.execute("SELECT reg_no FROM marriage_index WHERE id = %s", (record_id,))
            else:
                raise ValueError("Unknown window type")

            record = cursor.fetchone()
            if record:
                reg_no = record[0]
            else:
                print(f"No record found for record id: {record_id}")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Could not find record in database.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            # Open a dialog for the user to enter remarks
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Add Remarks - {form_type}")
            dialog.setGeometry(100, 100, 500, 300)
            dialog.setStyleSheet("background-color: #FFFFFF;")
            
            layout = QVBoxLayout()
            
            label = QLabel(f"Registration No: {reg_no}\nForm Type: {form_type}\n\nEnter remarks:")
            label.setStyleSheet("""
                QLabel {
                    color: #212121;
                    font-weight: bold;
                    padding: 5px;
                }
            """)
            layout.addWidget(label)
            
            text_edit = QPlainTextEdit()
            text_edit.setPlaceholderText("Enter your remarks here...")
            text_edit.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #FFFFFF;
                    color: #212121;
                    border: 1px solid #D1D0D0;
                    border-radius: 5px;
                    padding: 5px;
                    font-family: Arial;
                    font-size: 10pt;
                }
                QPlainTextEdit:focus {
                    border: 1px solid #ce305e;
                    background-color: #fef2f4;
                }
            """)
            layout.addWidget(text_edit)
            
            button_layout = QHBoxLayout()
            save_button = QPushButton("Save")
            cancel_button = QPushButton("Cancel")
            
            # Style buttons
            button_style = """
                QPushButton {
                    background-color: #ce305e;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #e0446a;
                }
                QPushButton:pressed {
                    background-color: #a82348;
                }
            """
            save_button.setStyleSheet(button_style)
            cancel_button.setStyleSheet(button_style)
            
            button_layout.addWidget(save_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            # Connect button clicks
            save_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            # Show dialog
            if dialog.exec() == QDialog.Accepted:
                remarks = text_edit.toPlainText()
                
                # Update database
                cursor.execute(
                    f"UPDATE {table_name} SET remarks = %s WHERE id = %s",
                    (remarks, record_id)
                )
                conn.commit()
                
                # Log the action
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "REMARKS_ADDED",
                    {"table": table_name, "reg_no": reg_no, "remarks": remarks[:100]}
                )
                conn.commit()
                
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Information)
                box.setWindowTitle("Success")
                box.setText("Remarks saved successfully.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
            
        except Exception as e:
            print(f"Error adding remarks: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to add remarks: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            if cursor:
                cursor.close()
            self.closeConnection()

    def open_form_file(self):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPENED",
                {"form_type": "1A/2A/3A", "path": self.form_file}
            )
            conn.commit()
            self.open_file(self.form_file)
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPEN_ERROR",
                {"form_type": "1A/2A/3A", "error": str(e)}
            )
            conn.commit()
            # QMessageBox.critical(self, "Error", f"Failed to open form: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to open form: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()

    def open_no_record(self):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPENED",
                {"form_type": "No Record", "path": self.no_record_file}
            )
            conn.commit()
            self.open_file(self.no_record_file)
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPEN_ERROR",
                {"form_type": "No Record", "error": str(e)}
            )
            conn.commit()
            # QMessageBox.critical(self, "Error", f"Failed to open form: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to open form: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()
    
    def open_destroyed_record(self):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPENED",
                {"form_type": "Destroyed", "path": self.destroyed_file}
            )
            conn.commit()
            self.open_file(self.destroyed_file)
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPEN_ERROR",
                {"form_type": "Destroyed", "error": str(e)}
            )
            conn.commit()
            # QMessageBox.critical(self, "Error", f"Failed to open form: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to open form: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()
    
    def open_selected_file(self, item):
        scanned = item.data(Qt.UserRole + 1)
        file_path = item.data(Qt.UserRole + 2)

        if not scanned or not file_path:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Record Not Yet Scanned")
            box.setText("This record has not been scanned yet, so there is no file to open.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
            return

        conn = self.create_connection()
        try:
            os.startfile(file_path)
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FILE_OPENED",
                {"file": os.path.basename(file_path), "path": file_path}
            )
            conn.commit()
        except FileNotFoundError:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"File not found:\n{file_path}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        except Exception as e:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"An error occurred:\n{str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FILE_OPEN_ERROR",
                {"error": str(e), "path": file_path}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def open_file(self, file_path):
        conn = self.create_connection()
        try:
            os.startfile(file_path)
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FILE_OPENED",
                {"path": file_path}
            )
            conn.commit()
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FILE_OPEN_ERROR",
                {"path": file_path, "error": str(e)}
            )
            conn.commit()
            # QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to open file: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()
    def search_pdfs(self):
        print(f"DEBUG - Current user during search: {self.current_user}")
        self.ui.results_list.clear()
        query = self.ui.search_textEdit.text().strip()
        self.found_pdfs.clear()

        conn = self.create_connection()
        try:
            search_type = self.ui.search_by_comboBox.currentText()
            
            print(f"DEBUG - Search parameters: type={search_type}, query={query}")
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "SEARCH_STARTED",
                {
                    "type": search_type,
                    "query": query
                }
            )
            conn.commit()

            if not query:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "SEARCH_ERROR",
                    {"error": "Empty search query"}
                )
                conn.commit()
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Please enter a name or date to search.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            # Determine which index table to use based on the window type
            if isinstance(self, VerifyBirthWindow):
                index_table = "birth_index"
                name_column = "name"
                date_column = "date_of_birth"
                form_type_label = "Certificate of Live Birth"
            elif isinstance(self, VerifyDeathWindow):
                index_table = "death_index"
                name_column = "name"
                date_column = "date_of_death"
                form_type_label = "Certificate of Death"
            elif isinstance(self, VerifyMarriageWindow):
                index_table = "marriage_index"
                name_column = "husband_name"  # We'll search both husband and wife names
                date_column = "date_of_marriage"
                form_type_label = "Certificate of Marriage"
            else:
                raise ValueError("Unknown window type")

            print(f"DEBUG - Using table: {index_table}, name_column: {name_column}, date_column: {date_column}")

            cursor = conn.cursor()
            
            try:
                # # First, verify if there are any records in the table
                # cursor.execute(f"SELECT COUNT(*) FROM {index_table}")
                # total_records = cursor.fetchone()[0]
                # print(f"DEBUG - Total records in {index_table}: {total_records}")

                # # Get a sample of existing records to help debug
                # cursor.execute(f"""
                #     SELECT name, date_of_birth, reg_no 
                #     FROM {index_table} 
                #     LIMIT 5
                # """)
                # sample_records = cursor.fetchall()
                # print("DEBUG - Sample records in database:")
                # for record in sample_records:
                #     print(f"  - Name: {record[0]}, Date: {record[1]}, Reg No: {record[2]}")

                if search_type == "Name":
                    if isinstance(self, VerifyMarriageWindow):
                        # For marriage records, search both husband and wife names
                        search_query = f"""
                            SELECT id, file_path, scanned, reg_no, date_of_reg FROM {index_table}
                            WHERE (
                                LOWER({name_column}) LIKE LOWER(%s) 
                                OR LOWER(wife_name) LIKE LOWER(%s)
                                OR LOWER({name_column}) LIKE LOWER(%s)
                                OR LOWER(wife_name) LIKE LOWER(%s)
                            )
                            ORDER BY {date_column} DESC
                        """
                        # Add variations of the name for more flexible matching
                        name_variations = [
                            f'%{query}%',
                            f'%{query.lower()}%',
                            f'%{query.upper()}%',
                            f'%{query.title()}%'
                        ]
                        search_params = name_variations
                    else:
                        search_query = f"""
                            SELECT id, file_path, scanned, reg_no, date_of_reg FROM {index_table}
                            WHERE (
                                LOWER({name_column}) LIKE LOWER(%s)
                                OR LOWER({name_column}) LIKE LOWER(%s)
                                OR LOWER({name_column}) LIKE LOWER(%s)
                                OR LOWER({name_column}) LIKE LOWER(%s)
                            )
                            ORDER BY {date_column} DESC
                        """
                        # Add variations of the name for more flexible matching
                        name_variations = [
                            f'%{query}%',
                            f'%{query.lower()}%',
                            f'%{query.upper()}%',
                            f'%{query.title()}%'
                        ]
                        search_params = name_variations
                elif search_type == "Date":
                    # Convert written date format to standard format
                    try:
                        from datetime import datetime
                        import re

                        # Common month mappings
                        month_map = {
                            'january': '01', 'february': '02', 'march': '03', 'april': '04',
                            'may': '05', 'june': '06', 'july': '07', 'august': '08',
                            'september': '09', 'october': '10', 'november': '11', 'december': '12',
                            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                            'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09',
                            'sept': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                        }

                        # Try to parse the date in various formats
                        date_str = query.lower().strip()
                        
                        # Handle written format with or without year (e.g., "December 17 2024" or "December 17")
                        written_pattern = r'([a-z]+)\s+(\d{1,2})(?:\s+(\d{4}))?'
                        written_match = re.match(written_pattern, date_str)
                        
                        if written_match:
                            month, day, year = written_match.groups()
                            if month in month_map:
                                # If year is provided, use it; otherwise, search for any year
                                if year:
                                    formatted_date = f"{year}-{month_map[month]}-{day.zfill(2)}"
                                    search_query = f"""
                                        SELECT id, file_path, scanned, reg_no, date_of_reg FROM {index_table}
                                        WHERE {date_column}::text LIKE %s
                                        OR {date_column}::text LIKE %s
                                        OR {date_column}::text LIKE %s
                                        ORDER BY {date_column} DESC
                                    """
                                    search_params = (
                                        f'%{formatted_date}%',
                                        f'%{query}%',
                                        f'%{month_map[month]}-{day.zfill(2)}%'
                                    )
                                else:
                                    # Search for month and day in any year
                                    search_query = f"""
                                        SELECT id, file_path, scanned, reg_no, date_of_reg FROM {index_table}
                                        WHERE {date_column}::text LIKE %s
                                        OR {date_column}::text LIKE %s
                                        OR {date_column}::text LIKE %s
                                        ORDER BY {date_column} DESC
                                    """
                                    search_params = (
                                        f'%{month_map[month]}-{day.zfill(2)}%',
                                        f'%{query}%',
                                        f'%{month} {day}%'
                                    )
                            else:
                                search_query = f"""
                                    SELECT id, file_path, scanned, reg_no, date_of_reg FROM {index_table}
                                    WHERE {date_column}::text LIKE %s
                                    ORDER BY {date_column} DESC
                                """
                                search_params = (f'%{query}%',)
                        else:
                            # Try to parse as standard date format
                            try:
                                # Try different date formats
                                date_formats = ['%Y-%m-%d', '%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y']
                                formatted_dates = []
                                
                                for date_format in date_formats:
                                    try:
                                        parsed_date = datetime.strptime(query, date_format)
                                        formatted_dates.append(parsed_date.strftime('%Y-%m-%d'))
                                    except ValueError:
                                        continue
                                
                                if formatted_dates:
                                    # Build a query that matches any of the formatted dates
                                    placeholders = ', '.join(['%s'] * len(formatted_dates))
                                    search_query = f"""
                                        SELECT id, file_path, scanned, reg_no, date_of_reg FROM {index_table}
                                        WHERE {date_column}::text LIKE ANY(ARRAY[{placeholders}])
                                        OR {date_column}::text LIKE %s
                                        ORDER BY {date_column} DESC
                                    """
                                    search_params = tuple(f'%{date}%' for date in formatted_dates) + (f'%{query}%',)
                                else:
                                    # If all parsing fails, do a simple text search
                                    search_query = f"""
                                        SELECT id, file_path, scanned, reg_no, date_of_reg FROM {index_table}
                                        WHERE {date_column}::text LIKE %s
                                        ORDER BY {date_column} DESC
                                    """
                                    search_params = (f'%{query}%',)
                            except Exception as e:
                                print(f"DEBUG - Date parsing error: {str(e)}")
                                # Fallback to simple text search
                                search_query = f"""
                                    SELECT id, file_path, scanned, reg_no, date_of_reg FROM {index_table}
                                    WHERE {date_column}::text LIKE %s
                                    ORDER BY {date_column} DESC
                                """
                                search_params = (f'%{query}%',)
                    except Exception as e:
                        print(f"DEBUG - Date parsing error: {str(e)}")
                        # Fallback to simple text search if date parsing fails
                        search_query = f"""
                            SELECT id, file_path, scanned, reg_no, date_of_reg FROM {index_table}
                            WHERE {date_column}::text LIKE %s
                            ORDER BY {date_column} DESC
                        """
                        search_params = (f'%{query}%',)
                elif search_type == "Reg No.":
                    search_query = f"""
                        SELECT id, file_path, scanned, reg_no, date_of_reg FROM {index_table}
                        WHERE reg_no LIKE %s
                        ORDER BY {date_column} DESC
                    """
                    search_params = (f'%{query}%',)

                print(f"DEBUG - Executing query: {search_query}")
                print(f"DEBUG - With parameters: {search_params}")
                
                cursor.execute(search_query, search_params)
                results = cursor.fetchall()
                
                print(f"DEBUG - Query returned {len(results)} results")

                if results:
                    display_texts = []
                    for row in results:
                        row_id, row_file_path, row_scanned, row_reg_no, row_date_of_reg = row
                        if row_scanned and row_file_path:
                            text = os.path.basename(row_file_path)
                        else:
                            year = str(row_date_of_reg.year) if row_date_of_reg else ""
                            text = f"{form_type_label} {year} (Reg. No. {row_reg_no}) - Record not yet scanned".replace("  ", " ")

                        item = QListWidgetItem(text)
                        item.setData(Qt.UserRole, row_id)
                        item.setData(Qt.UserRole + 1, bool(row_scanned))
                        item.setData(Qt.UserRole + 2, row_file_path)
                        self.ui.results_list.addItem(item)
                        display_texts.append(text)

                    self.found_pdfs.extend(display_texts)
                    self.ui.status_label.setText(f"Found {len(self.found_pdfs)} files.")
                    AuditLogger.log_action(
                        conn,
                        self.current_user,
                        "SEARCH_COMPLETED",
                        {
                            "result_count": len(display_texts),
                            "type": search_type
                        }
                    )
                else:
                    box = QMessageBox(self)
                    box.setIcon(QMessageBox.Information)
                    box.setWindowTitle("No Results")
                    box.setText("No records found.")
                    box.setStandardButtons(QMessageBox.Ok)
                    box.setStyleSheet(message_box_style)
                    box.exec()
                    AuditLogger.log_action(
                        conn,
                        self.current_user,
                        "SEARCH_NO_RESULTS",
                        {
                            "type": search_type,
                            "query": query
                        }
                    )
                conn.commit()
            except Exception as e:
                print(f"DEBUG - Database error: {str(e)}")
                raise e
        except Exception as e:
            print(f"DEBUG - General error: {str(e)}")
            AuditLogger.log_action(
                conn,
                self.current_user,
                "SEARCH_ERROR",
                {
                    "error": str(e),
                    "type": self.ui.search_by_comboBox.currentText(),
                    "query": query
                }
            )
            conn.commit()
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"An error occurred during search: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            if cursor:
                cursor.close()
            self.closeConnection()
            
            # Re-enable layout updates
            self.setUpdatesEnabled(True)
            self.update()
    
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
                everify.fullNameVerified.connect(self.populate_search_field)
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
    

    def show_search_window(self):
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
    
    def populate_search_field(self, full_name):
        
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "SEARCH_FIELD_POPULATED",
                {"full_name": full_name}
            )
            conn.commit()

            self.show_search_window()
            
            self.ui.search_textEdit.setText(full_name)
            self.ui.search_button.click()
            print(f"🔍 Auto-filled search_textEdit with: {full_name}")
        finally:
            self.closeConnection()

    def closeEvent(self, event):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_CLOSED",
                {"window": self.__class__.__name__}
            )
            conn.commit()

            # Clear all inputs
            self.ui.regyear_textEdit.clear()
            self.ui.search_textEdit.clear()
            self.ui.search_by_comboBox.setCurrentText("Name")
            self.ui.results_list.clear()
            self.ui.status_label.clear()

        finally:
            self.closeConnection()
            event.ignore()
            self.hide()

# Subclasses for each document type
class VerifyBirthWindow(VerifyWindowBase):
    def __init__(self, username, parent=None, main_window=None):
        super().__init__(Ui_SearchBirthWindow, r"\\server\MCR\LIVE BIRTH", r'forms\FORM 1-A.pdf', r'forms\FORM 1-B.pdf', r'forms\FORM 1-C.pdf', username, parent, main_window)

class VerifyDeathWindow(VerifyWindowBase):
    def __init__(self, username, parent=None, main_window=None):
        super().__init__(Ui_SearchDeathWindow, r"\\server\MCR\DEATH", r'forms\FORM 2-A.pdf', r'forms\FORM 2-B.pdf', r'forms\FORM 2-C.pdf', username, parent, main_window)

class VerifyMarriageWindow(VerifyWindowBase):
    def __init__(self, username, parent=None, main_window=None):
        super().__init__(Ui_SearchMarriageWindow, r"\\server\MCR\MARRIAGE", r'forms\FORM 3-A.pdf', r'forms\FORM 3-B.pdf', r'forms\FORM 3-C.pdf', username, parent, main_window)