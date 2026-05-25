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
from PySide6.QtCore import Qt, QDate, QSize, QUrl, QSettings
from PySide6.QtGui import QPixmap, QImage, QIcon, QShortcut, QKeySequence, QColor, QPalette
from PySide6.QtWebEngineWidgets import QWebEngineView
from utilities.stylesheets import button_style, date_picker_style, combo_box_style, message_box_style
from utilities.pdfviewer import PDFViewer
from utilities.audit_logger import AuditLogger
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from utilities.db_config import POSTGRES_CONFIG


class BirthTaggingWindow(QWidget):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.current_user = username
        self.connection = None
        self.setWindowTitle("Live Birth Records Tagging")
        self.setGeometry(100, 100, 1000, 600)
        # self.showMaximized()
        
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setWindowIcon(QIcon("assets/icons/application.png"))

        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #212121;
            }
            QLineEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
            QLineEdit:disabled {
                background-color: #fef2f4;
                color: #9E9E9E;
                border: 1px solid #CCCCCC;
            }
            QWidget#form_area[saved="true"] {
                background-color: #dff9e5; /* light green form background */
            }
            QWidget#form_area[saved="true"] QLabel {
                background-color: #dff9e5;
            }
            QComboBox {
                font-weight: bold;
            }
            QComboBox QLineEdit {
                font-weight: bold;
            }
            QDateEdit {
                font-weight: bold;
            }
        """)

        self.default_directory = r"\\server\MCR\LIVE BIRTH"
        self.selected_pdf = None
        self.last_page_no = None
        self.last_book_no = None
        self.last_reg_date = None
        self.last_place_of_birth = None

        self.settings = QSettings("OCCR", "RVS")
        self.pending_select_pdf = None
        self._initial_show = True

        self.init_ui()
    
    def create_connection(self):
        if self.connection is None:
            self.connection = psycopg2.connect(**POSTGRES_CONFIG)
            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return self.connection

    def _create_label(self, text):
        """Create a QLabel with AutoFillBackground enabled."""
        label = QLabel(text)
        label.setAutoFillBackground(True)
        return label

    def closeConnection(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignTop)
        
        # Select Folder Button
        self.folder_button = QPushButton("Select Folder")
        self.folder_button.setStyleSheet(button_style)
        self.folder_button.setFixedWidth(130)
        self.folder_button.clicked.connect(self.select_folder)
        main_layout.addWidget(self.folder_button)

        # Create a scroll area for the form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedWidth(750)
        
        # Create a widget to hold the form
        form_widget = QWidget()
        form_widget.setObjectName("form_area")
        self.form_area = form_widget
        form_layout = QVBoxLayout()
        form_layout.setAlignment(Qt.AlignTop)
        form_widget.setLayout(form_layout)

        # Create horizontal layouts for grouped fields
        # Page No, Book No, Registry No
        reg_info_layout = QHBoxLayout()
        reg_info_layout.setSpacing(10)
        
        page_no_container = QVBoxLayout()
        self.page_no_input = QLineEdit()
        self.page_no_input.setPlaceholderText("Page No.")
        self.page_no_input.setFixedWidth(220)
        page_no_container.addWidget(self._create_label("Page No.:"))
        page_no_container.addWidget(self.page_no_input)
        reg_info_layout.addLayout(page_no_container)

        book_no_container = QVBoxLayout()
        self.book_no_input = QLineEdit()
        self.book_no_input.setPlaceholderText("Book No.")
        self.book_no_input.setFixedWidth(220)
        book_no_container.addWidget(self._create_label("Book No.:"))
        book_no_container.addWidget(self.book_no_input)
        reg_info_layout.addLayout(book_no_container)

        reg_no_container = QVBoxLayout()
        self.reg_no_input = QLineEdit()
        self.reg_no_input.setPlaceholderText("Registry No.")
        self.reg_no_input.setFixedWidth(220)
        reg_no_container.addWidget(self._create_label("Registry No.:"))
        reg_no_container.addWidget(self.reg_no_input)
        reg_info_layout.addLayout(reg_no_container)
        form_layout.addLayout(reg_info_layout)

        # Name and Sex
        name_sex_layout = QHBoxLayout()
        name_sex_layout.setSpacing(10)

        name_container = QVBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        self.name_input.setFixedWidth(450)
        name_container.addWidget(self._create_label("Name:"))
        name_container.addWidget(self.name_input)
        name_sex_layout.addLayout(name_container)

        sex_container = QVBoxLayout()
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(["MALE", "FEMALE", "NO ENTRY"])
        self.sex_combo.setFixedWidth(220)
        self.sex_combo.setStyleSheet(combo_box_style)
        sex_container.addWidget(self._create_label("Sex:"))
        sex_container.addWidget(self.sex_combo)
        name_sex_layout.addLayout(sex_container)
        form_layout.addLayout(name_sex_layout)

        # Date of Birth and Place of Birth
        birth_info_layout = QHBoxLayout()
        birth_info_layout.setSpacing(10)

        dob_container = QVBoxLayout()
        dob_label_layout = QHBoxLayout()
        dob_label_layout.setSpacing(5)
        dob_label_layout.addWidget(self._create_label("Date of Birth:"))
        self.has_date_of_birth_check = QCheckBox("Has Date")
        self.has_date_of_birth_check.setChecked(True)
        self.has_date_of_birth_check.setStyleSheet("""
            QCheckBox::indicator:checked {
                background-color: #ce305e;
                border: 1px solid #ce305e;
            }
        """)
        self.has_date_of_birth_check.stateChanged.connect(lambda: self.date_of_birth_input.setEnabled(self.has_date_of_birth_check.isChecked()))
        dob_label_layout.addWidget(self.has_date_of_birth_check)
        dob_label_layout.addStretch()
        dob_container.addLayout(dob_label_layout)
        self.date_of_birth_input = QDateEdit()
        self.date_of_birth_input.setCalendarPopup(True)
        self.date_of_birth_input.setDate(QDate.currentDate())
        self.date_of_birth_input.setFixedWidth(150)
        self.date_of_birth_input.setStyleSheet(date_picker_style)
        self.date_of_birth_input.setEnabled(True)
        dob_container.addWidget(self.date_of_birth_input)
        birth_info_layout.addLayout(dob_container)

        pob_container = QVBoxLayout()
        self.place_of_birth_combo = QComboBox()
        self.place_of_birth_combo.setEditable(True)
        self.place_of_birth_combo.addItems([
            "SALVACION OPPUS YÑIGUEZ MEMORIAL PROVINCIAL HOSPITAL",
            "MAASIN MEDCITY HOSPITAL",
            "LIVINGHOPE HOSPITAL, INC.",
            "CM MATERNITY CLINIC",
            "NO ENTRY",
        ])
        self.place_of_birth_combo.setFixedWidth(400)
        self.place_of_birth_combo.setStyleSheet(combo_box_style)
        pob_container.addWidget(self._create_label("Place of Birth:"))
        pob_container.addWidget(self.place_of_birth_combo)
        birth_info_layout.addLayout(pob_container)

        type_of_birth_container = QVBoxLayout()
        self.type_of_birth_combo = QComboBox()
        self.type_of_birth_combo.addItems([
            "SINGLE", "TWIN", "TRIPLET", "QUADRUPLET", "QUINTUPLET", 
            "SEXTUPLET", "SEPTUPLET", "OCTUPLET", "NONUPLET", "DECAPLET", "NO ENTRY"
        ])
        self.type_of_birth_combo.setFixedWidth(100)
        self.type_of_birth_combo.setStyleSheet(combo_box_style)
        type_of_birth_container.addWidget(self._create_label("Type of Birth:"))
        type_of_birth_container.addWidget(self.type_of_birth_combo)
        birth_info_layout.addLayout(type_of_birth_container)
        form_layout.addLayout(birth_info_layout)

        # Name of Mother and Nationality
        mother_info_layout = QHBoxLayout()
        mother_info_layout.setSpacing(10)

        mother_name_container = QVBoxLayout()
        self.mother_name_input = QLineEdit()
        self.mother_name_input.setPlaceholderText("Name of Mother")
        self.mother_name_input.setFixedWidth(350)
        mother_name_container.addWidget(self._create_label("Name of Mother:"))
        mother_name_container.addWidget(self.mother_name_input)
        mother_info_layout.addLayout(mother_name_container)

        mother_nat_container = QVBoxLayout()
        self.mother_nationality_combo = QComboBox()
        self.mother_nationality_combo.setEditable(True)
        self.mother_nationality_combo.addItems([
            "FILIPINO",
            "CHINESE",
            "INDIAN",
            "AMERICAN",
            "JAPANESE",
            "SOUTH KOREAN",
            "GERMAN",
            "AUSTRALIAN",
            "TAIWANESE",
            "INDONESIAN",
            "VIETNAMESE",
            "NO ENTRY"
        ])
        self.mother_nationality_combo.setFixedWidth(220)
        self.mother_nationality_combo.setStyleSheet(combo_box_style)
        mother_nat_container.addWidget(self._create_label("Nationality of Mother:"))
        mother_nat_container.addWidget(self.mother_nationality_combo)
        mother_info_layout.addLayout(mother_nat_container)

        mother_age_container = QVBoxLayout()
        self.mother_age_input = QLineEdit()
        self.mother_age_input.setPlaceholderText("Age of Mother")
        self.mother_age_input.setFixedWidth(100)
        mother_age_container.addWidget(self._create_label("Age of Mother:"))
        mother_age_container.addWidget(self.mother_age_input)
        mother_info_layout.addLayout(mother_age_container)
        form_layout.addLayout(mother_info_layout)

        # Resident Information
        resident_layout = QHBoxLayout()
        resident_layout.setSpacing(10)

        maasin_resident_container = QVBoxLayout()
        self.maasin_resident_combo = QComboBox()
        self.maasin_resident_combo.addItems(["NO", "YES", "NO ENTRY"])
        self.maasin_resident_combo.setFixedWidth(150)
        self.maasin_resident_combo.setStyleSheet(combo_box_style)
        maasin_resident_container.addWidget(self._create_label("Maasin Resident:"))
        maasin_resident_container.addWidget(self.maasin_resident_combo)
        resident_layout.addLayout(maasin_resident_container)

        soleyte_resident_container = QVBoxLayout()
        self.soleyte_resident_combo = QComboBox()
        self.soleyte_resident_combo.addItems(["NO", "YES", "NO ENTRY"])
        self.soleyte_resident_combo.setFixedWidth(150)
        self.soleyte_resident_combo.setStyleSheet(combo_box_style)
        soleyte_resident_container.addWidget(self._create_label("Soleyte Resident:"))
        soleyte_resident_container.addWidget(self.soleyte_resident_combo)
        resident_layout.addLayout(soleyte_resident_container)

        leyte_resident_container = QVBoxLayout()
        self.leyte_resident_combo = QComboBox()
        self.leyte_resident_combo.addItems(["NO", "YES", "NO ENTRY"])
        self.leyte_resident_combo.setFixedWidth(150)
        self.leyte_resident_combo.setStyleSheet(combo_box_style)
        leyte_resident_container.addWidget(self._create_label("Leyte Resident:"))
        leyte_resident_container.addWidget(self.leyte_resident_combo)
        resident_layout.addLayout(leyte_resident_container)

        form_layout.addLayout(resident_layout)

        # Name of Father and Nationality
        father_info_layout = QHBoxLayout()
        father_info_layout.setSpacing(10)

        father_name_container = QVBoxLayout()
        self.father_name_input = QLineEdit()
        self.father_name_input.setPlaceholderText("Name of Father")
        self.father_name_input.setFixedWidth(350)
        father_name_container.addWidget(self._create_label("Name of Father:"))
        father_name_container.addWidget(self.father_name_input)
        father_info_layout.addLayout(father_name_container)

        father_nat_container = QVBoxLayout()
        self.father_nationality_combo = QComboBox()
        self.father_nationality_combo.setEditable(True)
        self.father_nationality_combo.addItems([
            "FILIPINO",
            "CHINESE",
            "INDIAN",
            "AMERICAN",
            "JAPANESE",
            "SOUTH KOREAN",
            "GERMAN",
            "AUSTRALIAN",
            "TAIWANESE",
            "INDONESIAN",
            "VIETNAMESE",
            "NO ENTRY"
        ])
        self.father_nationality_combo.setFixedWidth(220)
        self.father_nationality_combo.setStyleSheet(combo_box_style)
        father_nat_container.addWidget(self._create_label("Nationality of Father:"))
        father_nat_container.addWidget(self.father_nationality_combo)
        father_info_layout.addLayout(father_nat_container)

        father_age_container = QVBoxLayout()
        self.father_age_input = QLineEdit()
        self.father_age_input.setPlaceholderText("Age of Father")
        self.father_age_input.setFixedWidth(100)
        father_age_container.addWidget(self._create_label("Age of Father:"))
        father_age_container.addWidget(self.father_age_input)
        father_info_layout.addLayout(father_age_container)
        form_layout.addLayout(father_info_layout)

        # Place of Marriage and Date of Marriage
        marriage_info_layout = QHBoxLayout()
        marriage_info_layout.setSpacing(10)

        marriage_place_container = QVBoxLayout()
        self.marriage_place_input = QComboBox()
        self.marriage_place_input.setEditable(True)
        self.marriage_place_input.addItems([
            "NOT MARRIED",
            "FORGOTTEN",
            "DON'T KNOW",
            "NOT APPLICABLE",
            "MAASIN CITY, SOUTHERN LEYTE",
            "MACROHON, SOUTHERN LEYTE",
            "PADRE BURGOS, SOUTHERN LEYTE",
            "MALITBOG, SOUTHERN LEYTE",
            "TOMAS OPPUS, SOUTHERN LEYTE",
            "BONTOC, SOUTHERN LEYTE",
            "SOGOD, SOUTHERN LEYTE",
            "LIBAGON, SOUTHERN LEYTE",
            "LILOAN, SOUTHERN LEYTE",
            "SAN FRANCISCO, SOUTHERN LEYTE",
            "PINTUYAN, SOUTHERN LEYTE",
            "SAN RICARDO, SOUTHERN LEYTE",
            "SAINT BERNARD, SOUTHERN LEYTE",
            "SAN JUAN, SOUTHERN LEYTE",
            "ANAHAWAN, SOUTHERN LEYTE",
            "HINUNDAYAN, SOUTHERN LEYTE",
            "HINUNANGAN, SOUTHERN LEYTE",
            "SILAGO, SOUTHERN LEYTE",
            "LIMASAWA, SOUTHERN LEYTE",
            "MATALOM, LEYTE",
            "BATO, LEYTE",
            "HILONGOS, LEYTE",
            "NO ENTRY"
        ])
        self.marriage_place_input.setFixedWidth(450)
        self.marriage_place_input.setStyleSheet(combo_box_style)
        self.marriage_place_input.currentTextChanged.connect(self.handle_marriage_place_change)
        marriage_place_container.addWidget(self._create_label("Place of Marriage:"))
        marriage_place_container.addWidget(self.marriage_place_input)
        marriage_info_layout.addLayout(marriage_place_container)

        marriage_date_container = QVBoxLayout()
        marriage_date_label_layout = QHBoxLayout()
        marriage_date_label_layout.setSpacing(5)
        marriage_date_label_layout.addWidget(self._create_label("Date of Marriage:"))
        self.has_date_of_marriage_check = QCheckBox("Has Date")
        self.has_date_of_marriage_check.setChecked(True)
        self.has_date_of_marriage_check.setStyleSheet("""
            QCheckBox::indicator:checked {
                background-color: #ce305e;
                border: 1px solid #ce305e;
            }
        """)
        self.has_date_of_marriage_check.stateChanged.connect(lambda: self.date_of_marriage_input.setEnabled(self.has_date_of_marriage_check.isChecked()))
        marriage_date_label_layout.addWidget(self.has_date_of_marriage_check)
        marriage_date_label_layout.addStretch()
        marriage_date_container.addLayout(marriage_date_label_layout)
        self.date_of_marriage_input = QDateEdit()
        self.date_of_marriage_input.setCalendarPopup(True)
        self.date_of_marriage_input.setDate(QDate.currentDate())
        self.date_of_marriage_input.setEnabled(True)
        self.date_of_marriage_input.setFixedWidth(220)
        self.date_of_marriage_input.setStyleSheet(date_picker_style)
        marriage_date_container.addWidget(self.date_of_marriage_input)
        marriage_info_layout.addLayout(marriage_date_container)
        form_layout.addLayout(marriage_info_layout)

        # Attendant, Late Registration, Twin, and Date of Registration
        final_info_layout = QHBoxLayout()
        final_info_layout.setSpacing(10)

        attendant_container = QVBoxLayout()
        self.attendant_combo = QComboBox()
        self.attendant_combo.setEditable(True)
        self.attendant_combo.addItems([
            "PHYSICIAN",
            "MIDWIFE",
            "NURSE",
            "HILOT",
            "OTHERS",
            "NOT APPLICABLE",
            "DON'T KNOW",
            "NO ENTRY"
        ])
        self.attendant_combo.setFixedWidth(150)
        self.attendant_combo.setStyleSheet(combo_box_style)
        attendant_container.addWidget(self._create_label("Attendant:"))
        attendant_container.addWidget(self.attendant_combo)
        final_info_layout.addLayout(attendant_container)

        late_reg_container = QVBoxLayout()
        self.late_reg_combo = QComboBox()
        self.late_reg_combo.addItems(["NO", "YES", "NO ENTRY"])
        self.late_reg_combo.setFixedWidth(150)
        self.late_reg_combo.setStyleSheet(combo_box_style)
        late_reg_container.addWidget(self._create_label("Late Registration:"))
        late_reg_container.addWidget(self.late_reg_combo)
        final_info_layout.addLayout(late_reg_container)

        reg_date_container = QVBoxLayout()
        reg_date_label_layout = QHBoxLayout()
        reg_date_label_layout.setSpacing(5)
        reg_date_label_layout.addWidget(self._create_label("Date of Registration:"))
        self.has_date_of_reg_check = QCheckBox("Has Date")
        self.has_date_of_reg_check.setChecked(True)
        self.has_date_of_reg_check.setStyleSheet("""
            QCheckBox::indicator:checked {
                background-color: #ce305e;
                border: 1px solid #ce305e;
            }
        """)
        self.has_date_of_reg_check.stateChanged.connect(lambda: self.date_of_reg_input.setEnabled(self.has_date_of_reg_check.isChecked()))
        reg_date_label_layout.addWidget(self.has_date_of_reg_check)
        reg_date_label_layout.addStretch()
        reg_date_container.addLayout(reg_date_label_layout)
        self.date_of_reg_input = QDateEdit()
        self.date_of_reg_input.setCalendarPopup(True)
        self.date_of_reg_input.setDate(QDate.currentDate())
        self.date_of_reg_input.setFixedWidth(150)
        self.date_of_reg_input.setStyleSheet(date_picker_style)
        self.date_of_reg_input.setEnabled(True)
        reg_date_container.addWidget(self.date_of_reg_input)
        final_info_layout.addLayout(reg_date_container)
        form_layout.addLayout(final_info_layout)

        # Add the form widget to the scroll area
        scroll_area.setWidget(form_widget)
        main_layout.addWidget(scroll_area)

        # Action Buttons
        button_layout = QHBoxLayout()

        self.save_btn = QPushButton("Save Tags")
        self.save_btn.clicked.connect(self.save_tags)
        self.save_btn.setFixedWidth(130)
        button_layout.addWidget(self.save_btn)

        # Add keyboard shortcut for save button (Ctrl+S)
        save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        save_shortcut.activated.connect(self.save_tags)

        self.delete_btn = QPushButton("Delete Tags")
        self.delete_btn.clicked.connect(self.delete_tags)
        self.delete_btn.setFixedWidth(130)
        self.delete_btn.setEnabled(False)  # Disabled by default
        button_layout.addWidget(self.delete_btn)

        # Edit Button
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        self.edit_btn.setFixedWidth(130)
        self.edit_btn.setEnabled(False)  # Disabled by default
        button_layout.addWidget(self.edit_btn)

        self.save_btn.setStyleSheet(button_style)
        self.delete_btn.setStyleSheet(button_style)
        self.edit_btn.setStyleSheet(button_style)

        button_layout.setSpacing(5)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(Qt.AlignLeft)

        main_layout.addLayout(button_layout)

        # PDF List Preview
        self.pdf_list = QListWidget()
        self.pdf_list.setFixedWidth(750)
        self.pdf_list.setMaximumHeight(340)
        self.pdf_list.setIconSize(QSize(100, 140))
        self.pdf_list.itemClicked.connect(self.show_preview)
        self.pdf_list.setStyleSheet("""
            QListWidget {
                background-color: #FFFFFF;
                color: #212121;
            }
            QListWidget::item {
                background-color: #FFFFFF;
                color: #212121;
            }
            QListWidget::item:hover {
                background-color: #e0446a;
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                background-color: #ce305e;
                color: #FFFFFF;
            }
        """)

        self.pdf_list.currentItemChanged.connect(self.show_preview)
        main_layout.addWidget(self.pdf_list)

        # PDF Viewer Section
        pdf_layout = QVBoxLayout()
        pdf_controls = QHBoxLayout()

        self.pdf_viewer = PDFViewer()
        pdf_layout.addWidget(self.pdf_viewer)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.clicked.connect(self.zoom_in_pdf)
        zoom_in_btn.setStyleSheet(button_style)
        pdf_controls.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("-")
        zoom_out_btn.clicked.connect(self.zoom_out_pdf)
        zoom_out_btn.setStyleSheet(button_style)
        pdf_controls.addWidget(zoom_out_btn)

        pdf_layout.addLayout(pdf_controls)

        # Split Layout: Inputs Left, PDF Right
        split_layout = QHBoxLayout()
        split_layout.addLayout(main_layout, stretch=3)
        split_layout.addLayout(pdf_layout, stretch=5)

        self.setLayout(split_layout)

        # self.load_pdfs(self.default_directory)

    def select_folder(self):
        """Opens a folder selection dialog and loads PDFs."""
        conn = self.create_connection()
        try:
            folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", self.default_directory)
            if folder_path:
                # persist last selected folder
                self.settings.setValue("birth/last_folder", folder_path)
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "FOLDER_SELECTED",
                    {"path": folder_path}
                )
                conn.commit()
                self.load_pdfs(folder_path)
        finally:
            self.closeConnection()

    def load_pdfs(self, folder_path, selected_file_path=None):
        """Loads PDFs from a folder and generates thumbnails. Optionally selects a file."""
        conn = self.create_connection()
        progress = None
        try:
            self.pdf_list.clear()
            if not os.path.exists(folder_path):
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "PDF_LOAD_ERROR",
                    {"error": "Folder not found", "path": folder_path}
                )
                conn.commit()
                QMessageBox.warning(self, "Error", f"Folder not found: {folder_path}")
                return
            
            # Show loading progress
            progress = QProgressDialog("Loading PDFs...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("Loading")
            progress.setCancelButton(None)  # Remove cancel button
            progress.show()
            QApplication.processEvents()
            
            pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
            pdf_files.sort(key=self.natural_sort_key)
            
            failed_files = []
            for filename in pdf_files:
                try:
                    file_path = os.path.join(folder_path, filename)
                    thumbnail = self.generate_thumbnail(file_path)
                    
                    item = QListWidgetItem(QIcon(thumbnail), filename)
                    item.setSizeHint(QSize(0, 40))
                    item.setData(Qt.UserRole, file_path)
                    self.pdf_list.addItem(item)
                except Exception as e:
                    failed_files.append((filename, str(e)))
                    continue
            
            if failed_files:
                error_msg = "Failed to load some PDFs:\n\n"
                for filename, error in failed_files:
                    error_msg += f"{filename}: {error}\n"
                QMessageBox.warning(self, "Warning", error_msg)
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "PDFS_LOADED",
                {"folder": folder_path, "count": len(pdf_files), "failed": len(failed_files)}
            )
            conn.commit()

            # auto-select previously selected file if provided
            target = selected_file_path or self.pending_select_pdf
            if target:
                for i in range(self.pdf_list.count()):
                    item = self.pdf_list.item(i)
                    if item.data(Qt.UserRole) == target:
                        self.pdf_list.setCurrentItem(item)
                        self.show_preview(item)
                        break
                self.pending_select_pdf = None
            
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "PDF_LOAD_ERROR",
                {"error": str(e), "path": folder_path}
            )
            conn.commit()
            QMessageBox.critical(self, "Error", f"Failed to load PDFs: {str(e)}")
        finally:
            if progress:
                progress.close()
                progress.deleteLater()  # Ensure the dialog is properly destroyed
            self.closeConnection()

    def natural_sort_key(self, text):
        """Sort filenames naturally, treating numbers correctly."""
        def convert(text):
            return int(text) if text.isdigit() else text.lower()
        
        alphanum_key = [convert(c) for c in re.split('([0-9]+)', text)]
        return alphanum_key

    
    def generate_thumbnail(self, pdf_path):
        """Extracts the first page of a PDF and converts it to a QPixmap."""
        try:
            doc = pymupdf.open(pdf_path)
            if doc.page_count == 0:
                raise Exception("PDF has no pages")
            
            page = doc[0]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5))  # Scale down image
            
            # Convert raw image data to QImage
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGBA8888)
            
            # Clean up resources
            doc.close()
            
            return QPixmap.fromImage(img)
        except Exception as e:
            raise Exception(f"Failed to generate thumbnail: {str(e)}")

    def show_preview(self, item):
        """Loads the selected PDF and stores its file path."""
        # `currentItemChanged` can emit with `item=None` during selection transitions.
        if item is None:
            return

        # Avoid closing a shared connection while other code (e.g. `load_pdfs`)
        # is still using it. Only close if *we* created it.
        created_connection = self.connection is None
        conn = self.create_connection()
        try:
            self.selected_pdf = item.data(Qt.UserRole)
            if self.selected_pdf:
                # persist last selected PDF
                self.settings.setValue("birth/last_pdf", self.selected_pdf)
                self.last_page_no = self.page_no_input.text()
                self.last_book_no = self.book_no_input.text()
                self.last_reg_date = self.date_of_reg_input.date().toString("yyyy-MM-dd")
                self.last_place_of_birth = self.place_of_birth_combo.currentText()
                self.pdf_viewer.load_pdf(self.selected_pdf)
                self.load_existing_tags(self.selected_pdf)


                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "PDF_PREVIEWED",
                    {"file": self.selected_pdf}
                )
        finally:
            if created_connection:
                self.closeConnection()

    def get_selected_pdf(self):
        """Returns the currently selected PDF file path."""
        return self.selected_pdf


    def load_existing_tags(self, file_path):
        # Avoid closing a shared connection while other code (e.g. `load_pdfs`)
        # is still using it. Only close if *we* created it.
        created_connection = self.connection is None
        conn = self.create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    name, date_of_birth, sex, page_no, book_no, reg_no, 
                    date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                    name_of_father, nationality_father, parents_marriage_date,
                    parents_marriage_place, attendant, type_of_birth, late_registration,
                    maasin_resident, soleyte_resident, leyte_resident, mother_age, father_age
                FROM birth_index 
                WHERE file_path = %s
            """, (file_path,))

            result = cursor.fetchone()

            if result:
                (name, date_of_birth, sex, page_no, book_no, reg_no, 
                 date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                 name_of_father, nationality_father, parents_marriage_date,
                 parents_marriage_place, attendant, type_of_birth, late_registration,
                 maasin_resident, soleyte_resident, leyte_resident, mother_age, father_age) = result

                # Set QLineEdit values
                self.page_no_input.setText(str(page_no) if page_no else "")
                self.book_no_input.setText(str(book_no) if book_no else "")
                self.reg_no_input.setText(reg_no if reg_no else "")
                self.name_input.setText(name if name else "")
                self.mother_name_input.setText(name_of_mother if name_of_mother else "")
                self.father_name_input.setText(name_of_father if name_of_father else "")

                # Set QComboBox values
                self.sex_combo.setCurrentText(sex if sex else "NO ENTRY")
                self.place_of_birth_combo.setCurrentText(place_of_birth if place_of_birth else "NO ENTRY")
                self.mother_nationality_combo.setCurrentText(nationality_mother if nationality_mother else "NO ENTRY")
                self.father_nationality_combo.setCurrentText(nationality_father if nationality_father else "NO ENTRY")
                self.attendant_combo.setCurrentText(attendant if attendant else "NO ENTRY")
                # self.late_reg_combo.setCurrentText("Yes" if late_registration else "No")
                # self.twin_combo.setCurrentText("Yes" if twin else "No")
                # Force reset before setting
                self.late_reg_combo.setCurrentIndex(-1)  # This clears the selection
                self.late_reg_combo.setCurrentText("YES" if late_registration is True else "NO ENTRY" if late_registration is None else "NO")


                # Handle type_of_birth
                if type_of_birth:
                    self.type_of_birth_combo.setCurrentText(type_of_birth)
                else:
                    self.type_of_birth_combo.setCurrentText("NO ENTRY")

                # Set resident combo boxes
                self.maasin_resident_combo.setCurrentText("YES" if maasin_resident is True else "NO ENTRY" if maasin_resident is None else "NO")
                self.soleyte_resident_combo.setCurrentText("YES" if soleyte_resident is True else "NO ENTRY" if soleyte_resident is None else "NO")
                self.leyte_resident_combo.setCurrentText("YES" if leyte_resident is True else "NO ENTRY" if leyte_resident is None else "NO")

                # Handle dates with checkbox states
                if date_of_birth:
                    self.date_of_birth_input.setDate(QDate.fromString(date_of_birth.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                    self.has_date_of_birth_check.setChecked(True)
                else:
                    self.date_of_birth_input.setDate(QDate.currentDate())
                    self.has_date_of_birth_check.setChecked(False)
                    self.date_of_birth_input.setEnabled(False)

                if date_of_reg:
                    self.date_of_reg_input.setDate(QDate.fromString(date_of_reg.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                    self.has_date_of_reg_check.setChecked(True)
                else:
                    self.date_of_reg_input.setDate(QDate.currentDate())
                    self.has_date_of_reg_check.setChecked(False)
                    self.date_of_reg_input.setEnabled(False)

                # # Handle marriage place and date
                # if parents_marriage_place:
                #     self.marriage_place_input.setCurrentText(parents_marriage_place)
                # else:
                #     self.marriage_place_input.clearEditText()
                #     self.marriage_place_input.setCurrentIndex(0)
                #     self.marriage_place_input.setEditText(self.marriage_place_input.itemText(0))

                self.marriage_place_input.setCurrentText(parents_marriage_place if parents_marriage_place else "NO ENTRY")
                if parents_marriage_date:
                    self.date_of_marriage_input.setDate(QDate.fromString(parents_marriage_date.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                    self.has_date_of_marriage_check.setChecked(True)
                else:
                    self.has_date_of_marriage_check.setChecked(False)
                    self.date_of_marriage_input.setEnabled(False)

                self.mother_age_input.setText(str(mother_age) if mother_age is not None else "")
                self.father_age_input.setText(str(father_age) if father_age is not None else "")

                self.set_saved_cue(True)
            
            else:
                # Clear all fields
                self.page_no_input.setText(self.last_page_no)
                self.book_no_input.setText(self.last_book_no)
                self.reg_no_input.clear()
                self.name_input.clear()
                self.mother_name_input.clear()
                self.father_name_input.clear()
                
                self.sex_combo.setCurrentIndex(0)
                self.place_of_birth_combo.setCurrentText(self.last_place_of_birth)
                self.mother_nationality_combo.setCurrentIndex(0)
                self.father_nationality_combo.setCurrentIndex(0)
                self.attendant_combo.setCurrentIndex(0)
                self.late_reg_combo.setCurrentIndex(0)
                self.type_of_birth_combo.setCurrentIndex(0)
                self.maasin_resident_combo.setCurrentIndex(0)
                self.soleyte_resident_combo.setCurrentIndex(0)
                self.leyte_resident_combo.setCurrentIndex(0)
                self.mother_age_input.clear()
                self.father_age_input.clear()
                
                # Reset date checkboxes and enable date inputs
                self.has_date_of_birth_check.setChecked(True)
                self.date_of_birth_input.setDate(QDate.currentDate())
                self.date_of_birth_input.setEnabled(True)
                
                self.has_date_of_reg_check.setChecked(True)
                self.date_of_reg_input.setDate(QDate.fromString(self.last_reg_date, "yyyy-MM-dd"))
                self.date_of_reg_input.setEnabled(True)
                
                self.has_date_of_marriage_check.setChecked(True)
                self.date_of_marriage_input.setDate(QDate.currentDate())
                self.date_of_marriage_input.setEnabled(True)
                
                self.set_saved_cue(False)
        finally:
            if cursor:
                cursor.close()
            if created_connection:
                self.closeConnection()

    # def check_registry_number_exists(self, conn, reg_no, exclude_file_path=None):
    #     """Check if registry number already exists in the database."""
    #     if not reg_no or reg_no.strip() == "":
    #         return False, None
            
    #     cursor = conn.cursor()
    #     try:
    #         # Check if registry number exists, optionally excluding current file
    #         if exclude_file_path:
    #             cursor.execute("""
    #                 SELECT file_path, name FROM birth_index 
    #                 WHERE reg_no = %s AND file_path != %s
    #             """, (reg_no.strip(), exclude_file_path))
    #         else:
    #             cursor.execute("""
    #                 SELECT file_path, name FROM birth_index 
    #                 WHERE reg_no = %s
    #             """, (reg_no.strip(),))
            
    #         result = cursor.fetchone()
    #         return result is not None, result
    #     finally:
    #         if cursor:
    #             cursor.close()

    def save_tags(self):
        conn = self.create_connection()
        cursor = None
        try:
            if not self.selected_pdf:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAG_SAVE_FAILED",
                    {"reason": "no_pdf_selected"}
                )
                # QMessageBox.warning(self, "Error", "Please select a PDF file before saving tags!")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Please select a PDF file before saving tags.")
                box.setStandardButtons(QMessageBox.Ok)

                box.setStyleSheet(message_box_style)

                box.exec()
                return

            # Confirmation dialog before saving
            confirm_box = QMessageBox(self)
            confirm_box.setIcon(QMessageBox.Question)
            confirm_box.setWindowTitle("Confirm Save")
            confirm_box.setText("Are you sure you want to save these tags?")
            confirm_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm_box.setStyleSheet(message_box_style)
            
            if confirm_box.exec() != QMessageBox.Yes:
                return

            cursor = conn.cursor()

            try:
                # Get values from input fields
                page_no = int(self.page_no_input.text()) if self.page_no_input.text() else None
                book_no = int(self.book_no_input.text()) if self.book_no_input.text() else None
                reg_no = self.reg_no_input.text() 
                name = self.name_input.text() 
                # Handle date_of_birth based on checkbox
                date_of_birth = self.date_of_birth_input.date().toString("yyyy-MM-dd") if self.has_date_of_birth_check.isChecked() else None
                # Convert "NO ENTRY" to None for combo boxes
                sex = None if self.sex_combo.currentText() == "NO ENTRY" else self.sex_combo.currentText()
                # Handle date_of_reg based on checkbox
                date_of_reg = self.date_of_reg_input.date().toString("yyyy-MM-dd") if self.has_date_of_reg_check.isChecked() else None
                place_of_birth = None if self.place_of_birth_combo.currentText() == "NO ENTRY" else self.place_of_birth_combo.currentText()
                name_of_mother = self.mother_name_input.text()
                nationality_mother = None if self.mother_nationality_combo.currentText() == "NO ENTRY" else self.mother_nationality_combo.currentText()
                name_of_father = self.father_name_input.text() if self.father_name_input.text() != "" else None
                nationality_father = None if self.father_nationality_combo.currentText() == "NO ENTRY" else self.father_nationality_combo.currentText() if self.father_name_input.text() != "" else None
                type_of_birth = None if self.type_of_birth_combo.currentText() == "NO ENTRY" else self.type_of_birth_combo.currentText()
                
                # Handle marriage date based on marriage place and checkbox
                parents_marriage_place = self.marriage_place_input.currentText()
                parents_marriage_place = None if parents_marriage_place == "NO ENTRY" else parents_marriage_place
                if self.marriage_place_input.currentText() in ["NOT MARRIED", "FORGOTTEN", "DON'T KNOW", "NOT APPLICABLE"]:
                    parents_marriage_date = None
                else:
                    parents_marriage_date = self.date_of_marriage_input.date().toString("yyyy-MM-dd") if self.has_date_of_marriage_check.isChecked() else None
                
                attendant = None if self.attendant_combo.currentText() == "NO ENTRY" else self.attendant_combo.currentText()
                # Handle late_registration: YES->True, NO->False, NO ENTRY->None
                late_reg_text = self.late_reg_combo.currentText().strip()
                if late_reg_text == "NO ENTRY":
                    late_registration = None
                else:
                    late_registration = late_reg_text.lower() == "yes"
                mother_age = int(self.mother_age_input.text()) if self.mother_age_input.text() else None
                father_age = int(self.father_age_input.text()) if self.father_age_input.text() else None
                # Get resident values: YES->True, NO->False, NO ENTRY->None
                maasin_res_text = self.maasin_resident_combo.currentText().strip()
                maasin_resident = None if maasin_res_text == "NO ENTRY" else maasin_res_text.lower() == "yes"
                soleyte_res_text = self.soleyte_resident_combo.currentText().strip()
                soleyte_resident = None if soleyte_res_text == "NO ENTRY" else soleyte_res_text.lower() == "yes"
                leyte_res_text = self.leyte_resident_combo.currentText().strip()
                leyte_resident = None if leyte_res_text == "NO ENTRY" else leyte_res_text.lower() == "yes"
                
                cursor.execute("""
                    INSERT INTO birth_index (
                        file_path, name, date_of_birth, sex, page_no, book_no, reg_no,
                        date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                        name_of_father, nationality_father, parents_marriage_date,
                        parents_marriage_place, attendant, type_of_birth, late_registration,
                        maasin_resident, soleyte_resident, leyte_resident, mother_age, father_age
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT(file_path) DO UPDATE SET
                        name = EXCLUDED.name,
                        date_of_birth = EXCLUDED.date_of_birth,
                        sex = EXCLUDED.sex,
                        page_no = EXCLUDED.page_no,
                        book_no = EXCLUDED.book_no,
                        reg_no = EXCLUDED.reg_no,
                        date_of_reg = EXCLUDED.date_of_reg,
                        place_of_birth = EXCLUDED.place_of_birth,
                        name_of_mother = EXCLUDED.name_of_mother,
                        nationality_mother = EXCLUDED.nationality_mother,
                        name_of_father = EXCLUDED.name_of_father,
                        nationality_father = EXCLUDED.nationality_father,
                        parents_marriage_date = EXCLUDED.parents_marriage_date,
                        parents_marriage_place = EXCLUDED.parents_marriage_place,
                        attendant = EXCLUDED.attendant,
                        late_registration = EXCLUDED.late_registration,
                        type_of_birth = EXCLUDED.type_of_birth,
                        maasin_resident = EXCLUDED.maasin_resident,
                        soleyte_resident = EXCLUDED.soleyte_resident,
                        leyte_resident = EXCLUDED.leyte_resident,
                        mother_age = EXCLUDED.mother_age,
                        father_age = EXCLUDED.father_age
                """, (
                    self.selected_pdf, name, date_of_birth, sex, page_no, book_no, reg_no,
                    date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                    name_of_father, nationality_father, parents_marriage_date,
                    parents_marriage_place, attendant, type_of_birth, late_registration,
                    maasin_resident, soleyte_resident, leyte_resident, mother_age, father_age
                ))

                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAGS_SAVED",
                    {
                        "file": self.selected_pdf,
                        "record_type": "Birth"
                    }
                )
                # QMessageBox.information(self, "Success", "Tags saved successfully.")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Information)
                box.setWindowTitle("Success")
                box.setText("Tags saved successfully.")
                box.setStandardButtons(QMessageBox.Ok)

                box.setStyleSheet(message_box_style)
                box.exec()

                self.set_saved_cue(True)
                
            except Exception as e:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAG_SAVE_ERROR",
                    {
                        "error": str(e),
                        "file": self.selected_pdf,
                        "record_type": "Birth"
                    }
                )
                # QMessageBox.critical(self, "Error", f"Failed to save tags: {str(e)}")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Critical)
                box.setWindowTitle("Error")
                box.setText(f"Failed to save tags: {str(e)}")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
        finally:
            if cursor:
                cursor.close()
            self.closeConnection()

    def delete_tags(self):
        conn = self.create_connection()
        cursor = None
        try:
            if not self.selected_pdf:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAG_DELETE_FAILED",
                    {"reason": "no_pdf_selected"}
                )
                conn.commit()
                # QMessageBox.warning(self, "Error", "Please select a PDF file to delete its tags!")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Error")
                box.setText("Please select a PDF file to delete its tags.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            # Confirmation dialog before deleting
            confirm_box = QMessageBox(self)
            confirm_box.setIcon(QMessageBox.Warning)
            confirm_box.setWindowTitle("Confirm Delete")
            confirm_box.setText("Are you sure you want to delete these tags? This action cannot be undone.")
            confirm_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm_box.setStyleSheet(message_box_style)
            
            if confirm_box.exec() != QMessageBox.Yes:
                return

            cursor = conn.cursor()
            cursor.execute("DELETE FROM birth_index WHERE file_path = %s", (self.selected_pdf,))
            conn.commit()

            AuditLogger.log_action(
                conn,
                self.current_user,
                "TAGS_DELETED",
                {"file": self.selected_pdf, "table": "birth_index"}
            )
            conn.commit()

            # Clear all input fields after successful deletion
            self.page_no_input.clear()
            self.book_no_input.clear()
            self.reg_no_input.clear()
            self.name_input.clear()
            self.mother_name_input.clear()
            self.father_name_input.clear()
            
            self.sex_combo.setCurrentIndex(0)
            self.place_of_birth_combo.setCurrentIndex(0)
            self.mother_nationality_combo.setCurrentIndex(0)
            self.father_nationality_combo.setCurrentIndex(0)
            self.attendant_combo.setCurrentIndex(0)
            self.late_reg_combo.setCurrentIndex(0)
            self.type_of_birth_combo.setCurrentIndex(0)
            
            # Reset date checkboxes and enable date inputs
            self.has_date_of_birth_check.setChecked(True)
            self.date_of_birth_input.setDate(QDate.currentDate())
            self.date_of_birth_input.setEnabled(True)
            
            self.has_date_of_reg_check.setChecked(True)
            self.date_of_reg_input.setDate(QDate.currentDate())
            self.date_of_reg_input.setEnabled(True)
            
            self.has_date_of_marriage_check.setChecked(True)
            self.date_of_marriage_input.setDate(QDate.currentDate())
            self.date_of_marriage_input.setEnabled(True)
            
            self.mother_age_input.clear()
            self.father_age_input.clear()
            
            self.set_saved_cue(False)

            # QMessageBox.information(self, "Success", "Tags deleted successfully!")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Success")
            box.setText("Tags deleted successfully.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            if cursor:
                cursor.close()
            self.closeConnection()

    # def clear_all_tags(self):
    #     conn = self.create_connection()
    #     try:
    #         reply = QMessageBox.question(
    #             self, 
    #             "Clear All Tags", 
    #             "Are you sure you want to clear all tags from the database?",
    #             QMessageBox.Yes | QMessageBox.No, 
    #             QMessageBox.No
    #         )
            
    #         if reply == QMessageBox.Yes:
    #             cursor = conn.cursor()
    #             cursor.execute("DELETE FROM birth_index")
    #             conn.commit()

    #             AuditLogger.log_action(
    #                 conn,
    #                 self.current_user,
    #                 "ALL_TAGS_CLEARED",
    #                 {"tables": ["birth_index"]}
    #             )
    #             conn.commit()
    #             # QMessageBox.information(self, "Success", "All tags have been cleared from the database.")
    #             box = QMessageBox(self)
    #             box.setIcon(QMessageBox.Information)
    #             box.setWindowTitle("Success")
    #             box.setText("All tags have been cleared from the database.")
    #             box.setStandardButtons(QMessageBox.Ok)
    #             box.setStyleSheet(message_box_style)
    #             box.exec()
    #     finally:
    #         if cursor:
    #             cursor.close()
    #         self.closeConnection()

    def get_table_name(self, file_path):
        """Determine the table name based on file path or other logic."""
        return 'birth_index'
    
    def zoom_in_pdf(self):
        """Increase the zoom level of the PDF Viewer."""
        self.pdf_viewer.set_zoom(self.pdf_viewer.zoom_factor + 0.1)

    def zoom_out_pdf(self):
        """Decrease the zoom level of the PDF Viewer."""
        self.pdf_viewer.set_zoom(max(0.1, self.pdf_viewer.zoom_factor - 0.1))

    def showEvent(self, event):
        super().showEvent(event)
        conn = self.create_connection()
        try:
            # Only restore session state on initial window show, not on minimize/restore
            if self._initial_show:
                # attempt to restore last session state
                last_folder = self.settings.value("birth/last_folder", type=str)
                last_pdf = self.settings.value("birth/last_pdf", type=str)
                if last_folder and os.path.isdir(last_folder):
                    # keep for selection after load if file exists
                    if last_pdf and os.path.isfile(last_pdf):
                        self.pending_select_pdf = last_pdf
                    self.load_pdfs(last_folder)
                self._initial_show = False
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_OPENED",
                {"window": "BirthTaggingWindow"}
            )
            if not conn.closed:
                conn.commit()
        finally:
            if not conn.closed:
                self.closeConnection()

    def closeEvent(self, event):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_CLOSED",
                {"window": "BirthTaggingWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()
            event.ignore()
            self.hide()

    def handle_marriage_place_change(self, value):
        """Handle changes in marriage place combo box."""
        null_triggers = ["NOT MARRIED", "FORGOTTEN", "DON'T KNOW", "NOT APPLICABLE"]

        if value in null_triggers:
            # Set to null date and disable
            self.date_of_marriage_input.setDate(QDate())  # Clears the date
            self.date_of_marriage_input.setSpecialValueText("")  # Optional: show blank
            self.date_of_marriage_input.setEnabled(False)
        else:
            # Re-enable and set to current date if empty
            self.date_of_marriage_input.setEnabled(True)
            if not self.date_of_marriage_input.date().isValid() or self.date_of_marriage_input.date() == QDate():
                self.date_of_marriage_input.setDate(QDate.currentDate())



    def get_form_fields(self):
        """Return all form field widgets for enabling/disabling."""
        return [
            # Line edits
            self.page_no_input, self.book_no_input, self.reg_no_input, self.name_input,
            self.mother_name_input, self.father_name_input,
            # Combo boxes
            self.sex_combo, self.place_of_birth_combo, self.mother_nationality_combo,
            self.father_nationality_combo, self.attendant_combo, self.late_reg_combo,
            self.type_of_birth_combo, self.marriage_place_input,
            # Dates
            self.date_of_birth_input, self.date_of_reg_input, self.date_of_marriage_input,
            # Resident combos
            self.maasin_resident_combo, self.soleyte_resident_combo, self.leyte_resident_combo,
            # Age inputs
            self.mother_age_input, self.father_age_input,
        ]

    def disable_form_fields(self):
        """Disable all form input fields."""
        for field in self.get_form_fields():
            field.setEnabled(False)

    def enable_form_fields(self):
        """Enable all form input fields."""
        for field in self.get_form_fields():
            field.setEnabled(True)
        # Special handling for marriage date field
        if self.marriage_place_input.currentText() in ["NOT MARRIED", "FORGOTTEN", "DON'T KNOW", "NOT APPLICABLE"]:
            self.date_of_marriage_input.setEnabled(False)

    def _update_label_colors(self, background_color=None):
        """Update background colors of all labels in form_area."""
        if not hasattr(self, 'form_area') or self.form_area is None:
            return
        
        # Find all QLabel widgets in form_area and update their palette
        labels = self.form_area.findChildren(QLabel)
        for label in labels:
            label.setAutoFillBackground(True)
            palette = label.palette()
            if background_color:
                palette.setColor(QPalette.Window, background_color)
            else:
                palette.setColor(QPalette.Window, Qt.white)
            label.setPalette(palette)

    def set_saved_cue(self, enabled):
        """Manage field state and button states when tags are saved or deleted."""
        # Update label colors to white (no background color changes)
        self._update_label_colors(Qt.white)
        
        # Update field and button state
        if enabled:
            # Disable all fields after saving
            self.disable_form_fields()
            # Disable Save button, enable Edit and Delete buttons
            if hasattr(self, 'save_btn'):
                self.save_btn.setEnabled(False)
            if hasattr(self, 'delete_btn'):
                self.delete_btn.setEnabled(True)
            if hasattr(self, 'edit_btn'):
                self.edit_btn.setEnabled(True)
        else:
            # Enable all fields for editing (no tags yet or after deletion)
            self.enable_form_fields()
            # Enable Save button, disable Edit and Delete buttons when no tags
            if hasattr(self, 'save_btn'):
                self.save_btn.setEnabled(True)
            if hasattr(self, 'delete_btn'):
                self.delete_btn.setEnabled(False)
            if hasattr(self, 'edit_btn'):
                self.edit_btn.setEnabled(False)

    def on_edit_clicked(self):
        """Enable form fields when Edit button is clicked."""
        self.enable_form_fields()
        # Enable Save button for re-saving edited tags
        if hasattr(self, 'save_btn'):
            self.save_btn.setEnabled(True)
        # Keep Delete button enabled since tags still exist
        if hasattr(self, 'delete_btn'):
            self.delete_btn.setEnabled(True)
        self.edit_btn.setEnabled(False)



