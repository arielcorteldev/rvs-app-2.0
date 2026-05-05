import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# IMPORT PYSIDE6 MODULES
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *

# IMPORT UI 
from ui.Manage_User_Widget import Ui_Manage_User_Form
from utilities.audit_logger import AuditLogger
from utilities.db_config import POSTGRES_CONFIG

from utilities.stylesheets import button_style, message_box_style, table_style

# Manage Users Window
class ManageUserForm(QWidget, Ui_Manage_User_Form):
    def __init__(self, username, is_superuser=False, parent=None):
        super().__init__(parent)
        self.current_user = username
        self.is_superuser = is_superuser
        self.connection = None
        self.cursor = None

        # set up UI for window
        self.setupUi(self)

        # set window title for window
        self.setWindowTitle('Manage Users')

        self.groupBox.setStyleSheet("""
            QGroupBox {
                background-color: #F2F2F2;
            }
            QGroupBox::title {
                color: #616161;
                background-color: #F2F2F2;
            }
        """)

        # set maximum width for table widget
        self.tableWidget.setMaximumWidth(800)
        # set no. of columns for table
        self.tableWidget.setColumnCount(5)
        # set up width for columns
        self.tableWidget.setColumnWidth(0, 120)
        self.tableWidget.setColumnWidth(1, 120)
        self.tableWidget.setColumnWidth(2, 120)
        self.tableWidget.setColumnWidth(3, 120)
        self.tableWidget.setColumnWidth(4, 80)

        # set table labels 
        self.tableWidget.setHorizontalHeaderLabels(['First Name', 'Last Name', 'Username', 'Password', 'Superuser'])

        # hide the password column
        self.tableWidget.setColumnHidden(3, True)

        self.tableWidget.setStyleSheet(table_style)

        # connect buttons to methods
        self.add_button.clicked.connect(self.add_data)
        self.edit_button.clicked.connect(self.edit_data)
        self.update_button.clicked.connect(self.update_data)
        self.delete_button.clicked.connect(self.delete_data)

        # set styles for buttons
        self.add_button.setStyleSheet(button_style)
        self.edit_button.setStyleSheet(button_style)
        self.update_button.setStyleSheet(button_style)
        self.delete_button.setStyleSheet(button_style)

        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #212121;
                background-color: #F2F2F2;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D0D0;
                border-radius: 4px;
                padding: 5px;
                color: #212121;
            }
            QLineEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
        """)

        # hide password input
        self.password_input.setEchoMode(QLineEdit.Password)

        # Create superuser checkbox (will be shown/enabled only for superusers)
        self.superuser_checkbox = QCheckBox("Superuser")
        self.superuser_checkbox.setStyleSheet("""
            QCheckBox {
                color: #212121;
                background-color: #F2F2F2;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        # Initially hide the checkbox - will be shown only for superusers
        self.superuser_checkbox.setVisible(False)
        self.groupBox.layout().addWidget(self.superuser_checkbox)
        
        # Configure checkbox visibility based on user role
        self.configure_ui_for_user_role()

    # Configure UI based on user's superuser status
    def configure_ui_for_user_role(self):
        """Show/hide UI elements based on superuser status"""
        if self.is_superuser:
            self.superuser_checkbox.setVisible(True)
            self.add_button.setEnabled(True)
            self.delete_button.setEnabled(True)
        else:
            self.superuser_checkbox.setVisible(False)
            self.add_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    # Check if user has superuser permissions
    def check_superuser_permission(self):
        """Check if current user is a superuser. Show error if not."""
        if not self.is_superuser:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText("Access Denied")
            box.setWindowTitle("Insufficient Permissions")
            box.setDetailedText("Only superusers can perform this action.")
            box.setStyleSheet(message_box_style)
            box.exec()
            return False
        return True

    # create or open connection to database
    def create_connection(self):
        if self.connection is None:
            try:
                self.connection = psycopg2.connect(**POSTGRES_CONFIG)
                self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            except psycopg2.Error as e:
                # QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {str(e)}")
                box = QMessageBox()
                box.setIcon(QMessageBox.Critical)
                box.setText("Failed to connect to database")
                box.setWindowTitle("Database Error")
                box.setStyleSheet(message_box_style)
                box.exec()
                return None
        return self.connection

    def closeConnection(self):
        if self.connection:
            try:
                self.connection.close()
            except:
                pass  # Ignore close errors
            self.connection = None
            self.cursor = None

    def showEvent(self, event):
        super().showEvent(event)
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_OPENED",
                {"window": "ManageUserForm"}
            )
        finally:
            self.closeConnection()
        self.load_data()

    # load and display data in the table widget
    def load_data(self):
        try:
            conn = self.create_connection()
            if not conn:
                return
                
            cursor = conn.cursor()

            # If user is a superuser, show all users. If not, show only their own account
            if self.is_superuser:
                cursor.execute("SELECT COUNT(*) FROM users_list")
                count = cursor.fetchone()[0]
                cursor.execute("SELECT firstname, lastname, username, password, is_superuser FROM users_list ORDER BY firstname, lastname")
            else:
                # Non-superuser can only see their own account
                cursor.execute("SELECT COUNT(*) FROM users_list WHERE username = %s", (self.current_user,))
                count = cursor.fetchone()[0]
                cursor.execute("SELECT firstname, lastname, username, password, is_superuser FROM users_list WHERE username = %s", (self.current_user,))
            
            users = cursor.fetchall()

            self.tableWidget.setRowCount(count)
            
            for row, user in enumerate(users):
                for col, value in enumerate(user):
                    if col == 4:  # Superuser column
                        # Display Yes/No for superuser status
                        display_value = "Yes" if value else "No"
                        self.tableWidget.setItem(row, col, QTableWidgetItem(display_value))
                    else:
                        self.tableWidget.setItem(row, col, QTableWidgetItem(str(value)))

            self.tableWidget.setColumnHidden(3, True)  # Hide password column
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "USERS_LOADED",
                {"count": count, "is_superuser": self.is_superuser}
            )
            
        except psycopg2.Error as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "DATABASE_ERROR",
                {"operation": "load_data", "error": str(e)}
            )
            # QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setText("Failed to load data")
            box.setWindowTitle("Database Error")
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()

    # add user method
    def add_data(self):
        # Check if user has superuser permissions
        if not self.check_superuser_permission():
            return
            
        try:
            conn = self.create_connection()
            if not conn:
                return
                
            cursor = conn.cursor()

            fname = self.fname_input.text().strip()
            lname = self.lname_input.text().strip()
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()
            is_superuser = self.superuser_checkbox.isChecked()

            if not all([fname, lname, username, password]):
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "USER_CREATE_FAILED",
                    {"reason": "missing_information"}
                )
                # QMessageBox.warning(self, "Missing Information", "Please fill out all fields.")
                box = QMessageBox()
                box.setIcon(QMessageBox.Warning)
                box.setText("Missing Information")
                box.setWindowTitle("Missing Information")
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            # Check if user exists
            cursor.execute(
                "SELECT username FROM users_list WHERE firstname = %s AND lastname = %s",
                (fname, lname)
            )
            
            if cursor.fetchone():
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "USER_CREATE_FAILED",
                    {"reason": "duplicate_user", "name": f"{fname} {lname}"}
                )
                # QMessageBox.warning(self, "Duplicate User", "A user with this name already exists.")
                box = QMessageBox()
                box.setIcon(QMessageBox.Warning)
                box.setText("Duplicate User")
                box.setWindowTitle("Duplicate User")
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            # Insert new user
            cursor.execute('''
                INSERT INTO users_list (firstname, lastname, username, password, is_superuser)
                VALUES (%s, %s, %s, %s, %s)
            ''', (fname, lname, username, password, is_superuser))

            AuditLogger.log_action(
                conn,
                self.current_user,
                "USER_CREATED",
                {
                    "first_name": fname,
                    "last_name": lname,
                    "username": username,
                    "is_superuser": is_superuser
                }
            )
            
            # QMessageBox.information(self, "Success", "User successfully added!")
            box = QMessageBox()
            box.setIcon(QMessageBox.Information)
            box.setText("Success")
            box.setWindowTitle("Success")
            box.setStyleSheet(message_box_style)
            box.exec()

            # Clear inputs
            self.fname_input.clear()
            self.lname_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.superuser_checkbox.setChecked(False)

            # Refresh table
            self.load_data()

        except psycopg2.Error as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "DATABASE_ERROR",
                {"operation": "add_user", "error": str(e)}
            )
            # QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setText("Database Error")
            box.setWindowTitle("Database Error")
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()

    # edit user method
    def edit_data(self):
        # Check if user has superuser permissions or is editing themselves
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText("No Selection")
            box.setWindowTitle("No Selection")
            box.setStyleSheet(message_box_style)
            box.exec()
            return
        
        selected_username = self.tableWidget.item(current_row, 2).text()
        
        # Allow edit if: user is superuser OR user is editing their own account
        if not self.is_superuser and selected_username != self.current_user:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText("Access Denied")
            box.setWindowTitle("Insufficient Permissions")
            box.setDetailedText("You can only edit your own account.")
            box.setStyleSheet(message_box_style)
            box.exec()
            return
        
        try:
            self.fname_input.setText(self.tableWidget.item(current_row, 0).text())
            self.lname_input.setText(self.tableWidget.item(current_row, 1).text())
            self.username_input.setText(self.tableWidget.item(current_row, 2).text())
            self.password_input.setText(self.tableWidget.item(current_row, 3).text())
            
            # Get superuser status from database
            conn = self.create_connection()
            if not conn:
                return
                
            cursor = conn.cursor()
            cursor.execute("SELECT is_superuser FROM users_list WHERE username = %s", (selected_username,))
            result = cursor.fetchone()
            if result:
                self.superuser_checkbox.setChecked(result[0])
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "USER_EDIT_STARTED",
                {
                    "username": self.username_input.text(),
                    "first_name": self.fname_input.text(),
                    "last_name": self.lname_input.text()
                }
            )
            
        except Exception as e:
            # QMessageBox.critical(self, "Error", f"Failed to load user data: {str(e)}")
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setText("Error")
            box.setWindowTitle("Error")
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()

    # update user method
    def update_data(self):
        try:
            conn = self.create_connection()
            if not conn:
                return
                
            cursor = conn.cursor()
            
            current_row = self.tableWidget.currentRow()
            if current_row < 0:
                box = QMessageBox()
                box.setIcon(QMessageBox.Warning)
                box.setText("No Selection")
                box.setWindowTitle("No Selection")
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            old_username = self.tableWidget.item(current_row, 2).text()
            
            # Allow update if: user is superuser OR user is editing their own account
            if not self.is_superuser and old_username != self.current_user:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "USER_UPDATE_FAILED",
                    {"reason": "insufficient_permissions", "username": old_username}
                )
                box = QMessageBox()
                box.setIcon(QMessageBox.Warning)
                box.setText("Access Denied")
                box.setWindowTitle("Insufficient Permissions")
                box.setDetailedText("You can only edit your own account.")
                box.setStyleSheet(message_box_style)
                box.exec()
                return
            
            fname = self.fname_input.text().strip()
            lname = self.lname_input.text().strip()
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()
            is_superuser = self.superuser_checkbox.isChecked()

            if not all([fname, lname, username, password]):
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "USER_UPDATE_FAILED",
                    {"reason": "missing_information", "username": old_username}
                )
                # QMessageBox.warning(self, "Missing Information", "Please fill out all fields.")
                box = QMessageBox()
                box.setIcon(QMessageBox.Warning)
                box.setText("Missing Information")
                box.setWindowTitle("Missing Information")
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            # Check if new username already exists (if username was changed)
            if username != old_username:
                cursor.execute("SELECT username FROM users_list WHERE username = %s", (username,))
                if cursor.fetchone():
                    AuditLogger.log_action(
                        conn,
                        self.current_user,
                        "USER_UPDATE_FAILED",
                        {"reason": "username_exists", "username": username}
                    )
                    # QMessageBox.warning(self, "Username Exists", "This username is already taken.")
                    box = QMessageBox()
                    box.setIcon(QMessageBox.Warning)
                    box.setText("Username Exists")
                    box.setWindowTitle("Username Exists")
                    box.setStyleSheet(message_box_style)
                    box.exec()
                    return

            # Update user
            cursor.execute('''
                UPDATE users_list 
                SET firstname = %s, lastname = %s, username = %s, password = %s, is_superuser = %s
                WHERE username = %s
            ''', (fname, lname, username, password, is_superuser, old_username))

            AuditLogger.log_action(
                conn,
                self.current_user,
                "USER_UPDATED",
                {
                    "old_username": old_username,
                    "new_username": username,
                    "first_name": fname,
                    "last_name": lname,
                    "is_superuser": is_superuser
                }
            )
            
            # QMessageBox.information(self, "Success", "User successfully updated!")
            box = QMessageBox()
            box.setIcon(QMessageBox.Information)
            box.setText("Success")
            box.setWindowTitle("Success")
            box.setStyleSheet(message_box_style)
            box.exec()

            # Clear inputs
            self.fname_input.clear()
            self.lname_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.superuser_checkbox.setChecked(False)

            # Refresh table
            self.load_data()

        except psycopg2.Error as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "DATABASE_ERROR",
                {"operation": "update_user", "error": str(e)}
            )
            # QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setText("Database Error")
            box.setWindowTitle("Database Error")
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()

    # delete user method
    def delete_data(self):
        # Check if user has superuser permissions
        if not self.check_superuser_permission():
            return
            
        try:
            conn = self.create_connection()
            if not conn:
                return
                
            cursor = conn.cursor()
            
            current_row = self.tableWidget.currentRow()
            if current_row < 0:
                box = QMessageBox()
                box.setIcon(QMessageBox.Warning)
                box.setText("No Selection")
                box.setWindowTitle("No Selection")
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            username = self.tableWidget.item(current_row, 2).text()
            
            # Don't allow deleting the current user
            if username == self.current_user:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "USER_DELETE_FAILED",
                    {"reason": "cannot_delete_self", "username": username}
                )
                # QMessageBox.warning(self, "Cannot Delete", "You cannot delete your own account.")
                box = QMessageBox()
                box.setIcon(QMessageBox.Warning)
                box.setText("Cannot Delete")
                box.setWindowTitle("Cannot Delete")
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            reply = QMessageBox.question(
                self, 
                "Confirm Deletion",
                f"Are you sure you want to delete user '{username}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                cursor.execute("DELETE FROM users_list WHERE username = %s", (username,))
                
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "USER_DELETED",
                    {"deleted_username": username}
                )
                
                # QMessageBox.information(self, "Success", "User successfully deleted!")
                box = QMessageBox()
                box.setIcon(QMessageBox.Information)
                box.setText("Success")
                box.setWindowTitle("Success")
                box.setStyleSheet(message_box_style)
                box.exec()
                
                # Clear inputs
                self.fname_input.clear()
                self.lname_input.clear()
                self.username_input.clear()
                self.password_input.clear()
                self.superuser_checkbox.setChecked(False)
                
                # Refresh table
                self.load_data()

        except psycopg2.Error as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "DATABASE_ERROR",
                {"operation": "delete_user", "error": str(e)}
            )
            # QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setText("Database Error")
            box.setWindowTitle("Database Error")
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()

    # clear everything when window is closed
    def closeEvent(self, event):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_CLOSED",
                {"window": "ManageUserForm"}
            )
        finally:
            self.closeConnection()
            event.ignore()
            self.hide()