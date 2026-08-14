# controllers/digitization_status.py
"""
Digitization Status Tracker.

Lets staff see, at a glance, which Registry Books (SERVER/REGISTRY BOOKS)
and which Certificate years (SERVER/MCR) have been Scanned and/or Tagged
into the database - so they know whether a record should be searchable
in RVS yet.

Status is entered manually by Superusers (no live file-server scanning,
no auto-counting against birth_index/death_index/marriage_index - kept
deliberately simple per Ariel's call).
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QLabel, QLineEdit, QComboBox,
    QPushButton, QCheckBox, QDialog, QDialogButtonBox, QMessageBox,
    QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor
import psycopg2
from datetime import datetime

from utilities.db_config import POSTGRES_CONFIG
from utilities.audit_logger import AuditLogger
from utilities.stylesheets import table_style, combo_box_style, message_box_style
from utilities.digitization_constants import RECORD_TYPES, CATEGORIES


class DigitizationEntryDialog(QDialog):
    """Add or edit a single Book/Certificate-Year status entry."""

    def __init__(self, parent=None, existing=None):
        """
        existing: None for a new entry, or a dict with keys
        {id, record_type, category, label, scanned, tagged} to edit.
        """
        super().__init__(parent)
        self.existing = existing
        self.setWindowTitle("Edit Entry" if existing else "Add Entry")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.record_type_combo = QComboBox()
        self.record_type_combo.addItems(RECORD_TYPES)
        self.record_type_combo.setStyleSheet(combo_box_style)
        form.addRow("Record Type:", self.record_type_combo)

        self.category_combo = QComboBox()
        self.category_combo.addItems(CATEGORIES)
        self.category_combo.setStyleSheet(combo_box_style)
        form.addRow("Category:", self.category_combo)

        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("e.g. Book 1, or 2026")
        form.addRow("Label:", self.label_input)

        self.scanned_check = QCheckBox("Scanned")
        form.addRow("", self.scanned_check)

        self.tagged_check = QCheckBox("Tagged")
        form.addRow("", self.tagged_check)

        layout.addLayout(form)

        # Editing an existing entry: the identity fields (type/category/label)
        # are locked to avoid accidentally splitting one book into two rows.
        if existing:
            self.record_type_combo.setCurrentText(existing["record_type"])
            self.category_combo.setCurrentText(existing["category"])
            self.label_input.setText(existing["label"])
            self.scanned_check.setChecked(existing["scanned"])
            self.tagged_check.setChecked(existing["tagged"])
            self.record_type_combo.setEnabled(False)
            self.category_combo.setEnabled(False)
            self.label_input.setEnabled(False)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return {
            "record_type": self.record_type_combo.currentText(),
            "category": self.category_combo.currentText(),
            "label": self.label_input.text().strip(),
            "scanned": self.scanned_check.isChecked(),
            "tagged": self.tagged_check.isChecked(),
        }


class DigitizationStatusWindow(QMainWindow):
    def __init__(self, username, is_superuser, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Digitization Status Tracker")
        self.setMinimumSize(900, 550)
        self.current_user = username
        self.is_superuser = is_superuser

        self.icon = QIcon('assets/icons/handover.png')
        self.setWindowIcon(self.icon)

        self.setStyleSheet("""
            QMainWindow { background-color: #FFFFFF; }
            QLabel { font-weight: bold; color: #212121; }
            QLineEdit, QComboBox {
                padding: 5px;
                border: 1px solid #D1D0D0;
                border-radius: 4px;
                background-color: #FFFFFF;
                color: #212121;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                color: #FFFFFF;
                background-color: #ce305e;
            }
            QPushButton:hover { background-color: #e0446a; }
            QPushButton:disabled { background-color: #D1D0D0; color: #7A7A7A; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("Digitization Status Tracker")
        title.setStyleSheet("font-size: 18px; margin-bottom: 5px;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Shows which Registry Books and Certificate years are Scanned "
            "and/or Tagged, so staff know what's searchable in RVS."
        )
        subtitle.setStyleSheet("font-weight: normal; color: #6B6B6B; margin-bottom: 10px;")
        layout.addWidget(subtitle)

        # --- Filter row ---
        filter_layout = QHBoxLayout()

        self.type_filter = QComboBox()
        self.type_filter.addItem("All Record Types")
        self.type_filter.addItems(RECORD_TYPES)
        self.type_filter.setStyleSheet(combo_box_style)
        self.type_filter.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.type_filter)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.addItems(CATEGORIES)
        self.category_filter.setStyleSheet(combo_box_style)
        self.category_filter.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.category_filter)

        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("Search label (e.g. Book 1, 2026)")
        self.search_filter.textChanged.connect(self.load_data)
        filter_layout.addWidget(self.search_filter)

        filter_layout.addStretch()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_data)
        filter_layout.addWidget(self.refresh_button)

        self.add_button = QPushButton("Add Entry")
        self.add_button.clicked.connect(self.add_entry)
        self.add_button.setVisible(self.is_superuser)
        filter_layout.addWidget(self.add_button)

        layout.addLayout(filter_layout)

        if not self.is_superuser:
            note = QLabel("View only. Contact a Superuser to update status.")
            note.setStyleSheet("font-weight: normal; color: #9A9A9A; font-size: 11px;")
            layout.addWidget(note)

        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Record Type", "Category", "Label",
            "Scanned", "Tagged", "Last Updated"
        ])
        self.table.setColumnHidden(0, True)  # keep id around for edit/delete, hide from view
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(table_style)
        if self.is_superuser:
            self.table.cellDoubleClicked.connect(self.edit_entry)
        layout.addWidget(self.table)

        self.load_data()

    def create_connection(self):
        try:
            return psycopg2.connect(**POSTGRES_CONFIG)
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Database Error", f"Could not connect to database: {str(e)}")
            return None

    def closeConnection(self, conn=None):
        if conn:
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing connection: {str(e)}")

    def load_data(self):
        conn = self.create_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = """
                SELECT id, record_type, category, label, scanned, tagged, updated_at
                FROM digitization_status
                WHERE 1=1
            """
            params = []

            if self.type_filter.currentIndex() > 0:
                query += " AND record_type = %s"
                params.append(self.type_filter.currentText())

            if self.category_filter.currentIndex() > 0:
                query += " AND category = %s"
                params.append(self.category_filter.currentText())

            if self.search_filter.text():
                query += " AND label ILIKE %s"
                params.append(f"%{self.search_filter.text()}%")

            query += " ORDER BY record_type, category, label"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                row_id, record_type, category, label, scanned, tagged, updated_at = row

                self.table.setItem(i, 0, QTableWidgetItem(str(row_id)))
                self.table.setItem(i, 1, QTableWidgetItem(record_type))
                self.table.setItem(i, 2, QTableWidgetItem(category))
                self.table.setItem(i, 3, QTableWidgetItem(label))

                scanned_item = QTableWidgetItem("Scanned" if scanned else "Not Scanned")
                scanned_item.setForeground(QColor("#1E8E3E") if scanned else QColor("#B00020"))
                self.table.setItem(i, 4, scanned_item)

                tagged_item = QTableWidgetItem("Tagged" if tagged else "Not Tagged")
                tagged_item.setForeground(QColor("#1E8E3E") if tagged else QColor("#B00020"))
                self.table.setItem(i, 5, tagged_item)

                updated_str = updated_at.strftime("%Y-%m-%d %H:%M") if isinstance(updated_at, datetime) else str(updated_at)
                self.table.setItem(i, 6, QTableWidgetItem(updated_str))

            self.table.resizeColumnsToContents()
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        except psycopg2.Error as e:
            QMessageBox.critical(self, "Database Error", f"Error loading digitization status: {str(e)}")
        finally:
            self.closeConnection(conn)

    def add_entry(self):
        if not self.is_superuser:
            return

        dialog = DigitizationEntryDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        values = dialog.get_values()
        if not values["label"]:
            QMessageBox.warning(self, "Input Error", "Label is required.")
            return

        conn = self.create_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO digitization_status
                (record_type, category, label, scanned, tagged, updated_by, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (
                values["record_type"], values["category"], values["label"],
                values["scanned"], values["tagged"], self.current_user
            ))
            conn.commit()

            AuditLogger.log_action(
                conn, self.current_user, "DIGITIZATION_STATUS_ADDED", values
            )
            conn.commit()

        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            QMessageBox.warning(
                self, "Duplicate Entry",
                f"An entry for {values['record_type']} / {values['category']} / "
                f"{values['label']} already exists. Double-click it to edit instead."
            )
            return
        except psycopg2.Error as e:
            conn.rollback()
            QMessageBox.critical(self, "Database Error", f"Error adding entry: {str(e)}")
            return
        finally:
            self.closeConnection(conn)

        self.load_data()

    def edit_entry(self, row, column):
        if not self.is_superuser:
            return

        row_id = int(self.table.item(row, 0).text())
        existing = {
            "id": row_id,
            "record_type": self.table.item(row, 1).text(),
            "category": self.table.item(row, 2).text(),
            "label": self.table.item(row, 3).text(),
            "scanned": self.table.item(row, 4).text() == "Scanned",
            "tagged": self.table.item(row, 5).text() == "Tagged",
        }

        dialog = DigitizationEntryDialog(self, existing=existing)

        delete_button = QPushButton("Delete Entry")
        delete_button.setStyleSheet("background-color: #7A7A7A;")
        dialog.layout().insertWidget(dialog.layout().count() - 1, delete_button)
        delete_button.clicked.connect(lambda: self.delete_entry(dialog, row_id))

        if dialog.exec() != QDialog.Accepted:
            return

        values = dialog.get_values()
        conn = self.create_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE digitization_status
                SET scanned = %s, tagged = %s, updated_by = %s, updated_at = NOW()
                WHERE id = %s
            """, (values["scanned"], values["tagged"], self.current_user, row_id))
            conn.commit()

            AuditLogger.log_action(
                conn, self.current_user, "DIGITIZATION_STATUS_UPDATED",
                {"id": row_id, **values}
            )
            conn.commit()

        except psycopg2.Error as e:
            conn.rollback()
            QMessageBox.critical(self, "Database Error", f"Error updating entry: {str(e)}")
            return
        finally:
            self.closeConnection(conn)

        self.load_data()

    def delete_entry(self, dialog, row_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Delete this entry? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        conn = self.create_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM digitization_status WHERE id = %s", (row_id,))
            conn.commit()

            AuditLogger.log_action(
                conn, self.current_user, "DIGITIZATION_STATUS_DELETED", {"id": row_id}
            )
            conn.commit()

        except psycopg2.Error as e:
            conn.rollback()
            QMessageBox.critical(self, "Database Error", f"Error deleting entry: {str(e)}")
            return
        finally:
            self.closeConnection(conn)

        dialog.reject()
        self.load_data()

    def closeEvent(self, event):
        conn = self.create_connection()
        try:
            if conn:
                AuditLogger.log_action(
                    conn, self.current_user, "DIGITIZATION_STATUS_WINDOW_CLOSED",
                    {"message": "Digitization Status window closed"}
                )
                conn.commit()
        finally:
            self.closeConnection(conn)
            event.ignore()
            self.hide()
