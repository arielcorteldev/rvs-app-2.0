import psycopg2
from datetime import datetime
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdf_canvas
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QIcon
from utilities.stylesheets import button_style, date_picker_style
from utilities.audit_logger import AuditLogger
from utilities.db_config import POSTGRES_CONFIG
from utilities.stylesheets import *




class StatisticsWindow(QWidget):
    AGE_RANGE_BREAKDOWN_KEYS = {
        "Mother Age (Youngest/Oldest)",
        "Father Age (Youngest/Oldest)",
        "Age (Youngest/Oldest)",
        "Husband Age (Youngest/Oldest)",
        "Wife Age (Youngest/Oldest)",
    }

    # Key to column mapping - centralized to avoid duplication
    KEY_COLUMN_MAP = {
        # Live Birth
        "Name": "name",
        "Sex": "sex",
        "Place of Birth": "place_of_birth",
        "Name of Mother": "name_of_mother",
        "Name of Father": "name_of_father",
        "Nationality of Mother": "nationality_mother",
        "Nationality of Father": "nationality_father",
        "Attendant": "attendant",
        "Late Registration": "late_registration",
        "Type of Birth": "type_of_birth",
        "Mother Age": "mother_age",
        "Father Age": "father_age",
        # Death
        "Age": "age_years",
        "Civil Status": "civil_status",
        "Nationality": "nationality",
        "Place of Death": "place_of_death",
        "Cause of Death": "cause_of_death",
        "Corpse Disposal": "corpse_disposal",
        # Marriage
        "Husband Name": "husband_name",
        "Husband Age": "husband_age",
        "Husband Civil Status": "husb_civil_status",
        "Husband Nationality": "husb_nationality",
        "Nationality of Husband": "husb_nationality",
        "Wife Name": "wife_name",
        "Wife Age": "wife_age",
        "Wife Civil Status": "wife_civil_status",
        "Wife Nationality": "wife_nationality",
        "Nationality of Wife": "wife_nationality",
        "Place of Marriage": "place_of_marriage",
        "Ceremony Type": "ceremony_type",
        # Resident filters
        "Maasin Residents": "maasin_resident",
        "SoLeyte Residents (Excl. Maasin)": "soleyte_resident_excl_maasin",
        "SoLeyte Residents (Incl. Maasin)": "soleyte_resident",
        "Leyte Residents": "leyte_resident",
        "Residents outside Leyte": "residents_outside_leyte",
    }

    # Breakdown mode keys per record type
    BREAKDOWN_KEYS = {
        "Live Birth": ["All", "Monthly Totals", "Sex", "Place of Birth", "Nationality of Mother", "Nationality of Father", "Mother Age (Youngest/Oldest)", "Father Age (Youngest/Oldest)", "Legitimate", "Attendant", "Type of Birth", "Late Registration"],
        "Death": ["All", "Monthly Totals", "Sex", "Civil Status", "Nationality", "Age (Youngest/Oldest)", "Place of Death", "Attendant", "Corpse Disposal", "Late Registration"],
        "Marriage": ["All", "Monthly Totals", "Husband Civil Status", "Wife Civil Status", "Nationality of Husband", "Nationality of Wife", "Husband Age (Youngest/Oldest)", "Wife Age (Youngest/Oldest)", "Ceremony Type", "Late Registration"],
    }

    # Total count mode keys per record type
    TOTAL_COUNT_KEYS = {
        "Live Birth": ["All", "Name", "Sex", "Place of Birth", "Name of Mother", "Name of Father", "Nationality of Mother", "Nationality of Father", "Attendant", "Type of Birth", "Late Registration", "Maasin Residents", "SoLeyte Residents (Excl. Maasin)", "SoLeyte Residents (Incl. Maasin)", "Leyte Residents", "Residents outside Leyte"],
        "Death": ["All", "Name", "Sex", "Age", "Civil Status", "Nationality", "Place of Death", "Cause of Death", "Attendant", "Corpse Disposal", "Late Registration", "Maasin Residents", "SoLeyte Residents (Excl. Maasin)", "SoLeyte Residents (Incl. Maasin)", "Leyte Residents", "Residents outside Leyte"],
        "Marriage": ["All", "Husband Name", "Husband Age", "Husband Civil Status", "Husband Nationality", "Wife Name", "Wife Age", "Wife Civil Status", "Wife Nationality", "Place of Marriage", "Ceremony Type", "Late Registration"],
    }

    # Secondary filter keys (all available filters)
    SECONDARY_FILTER_KEYS = {
        "Live Birth": ["None", "Sex", "Place of Birth", "Name of Mother", "Name of Father", "Nationality of Mother", "Nationality of Father", "Attendant", "Type of Birth", "Maasin Residents", "SoLeyte Residents (Excl. Maasin)", "SoLeyte Residents (Incl. Maasin)", "Leyte Residents", "Residents outside Leyte"],
        "Death": ["None", "Sex", "Age", "Civil Status", "Nationality", "Place of Death", "Cause of Death", "Attendant", "Corpse Disposal", "Maasin Residents", "SoLeyte Residents (Excl. Maasin)", "SoLeyte Residents (Incl. Maasin)", "Leyte Residents", "Residents outside Leyte"],
        "Marriage": ["None", "Husband Name", "Husband Age", "Husband Civil Status", "Husband Nationality", "Wife Name", "Wife Age", "Wife Civil Status", "Wife Nationality", "Place of Marriage", "Ceremony Type"],
    }

    # ComboBox style
    COMBOBOX_STYLE = """
        QComboBox {
            background-color: #FFFFFF;
            color: #212121;
            border-radius: 4px;
            padding: 4px;
            border: 1px solid #D1D0D0;
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
    """
    
    LINEEDIT_STYLE = """
        QLineEdit {
            background-color: #FFFFFF;
            color: #212121;
            border-radius: 4px;
            padding: 6px;
            border: 1px solid #D1D0D0;
        }
        QLineEdit:focus {
            border: 1px solid #ce305e;
            background-color: #fef2f4;
        }
    """

    SPINBOX_STYLE = """
        QSpinBox {
            background-color: #FFFFFF;
            color: #212121;
            border-radius: 4px;
            padding: 4px;
            border: 1px solid #D1D0D0;
        }
        QSpinBox:focus {
            border: 1px solid #ce305e;
            background-color: #fef2f4;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #f0f0f0;
            border: 1px solid #D1D0D0;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #ce305e;
        }
    """

    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.current_user = username
        self.connection = None
        self.setWindowTitle("Statistics Tool")
        self.setGeometry(200, 200, 600, 400)
        self.setWindowIcon(QIcon("assets/icons/application.png"))
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
        """)
        self.init_ui()

    def create_connection(self):
        if self.connection is None:
            self.connection = psycopg2.connect(**POSTGRES_CONFIG)
            self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        return self.connection

    def closeConnection(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

    def init_ui(self):
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)

        # Record Type label
        record_type_label = QLabel("Record Type:", self)
        record_type_label.setStyleSheet("font-weight: bold; color: #212121;")
        left_layout.addWidget(record_type_label)

        # Record type selection dropdown
        self.record_type_dropdown = QComboBox(self)
        self.record_type_dropdown.addItems(["Live Birth", "Death", "Marriage"])
        self.record_type_dropdown.setStyleSheet(self.COMBOBOX_STYLE)
        self.record_type_dropdown.currentIndexChanged.connect(self.on_record_type_changed)
        left_layout.addWidget(self.record_type_dropdown)

        # Output Mode label
        output_mode_label = QLabel("Output Mode:", self)
        output_mode_label.setStyleSheet("font-weight: bold; color: #212121;")
        left_layout.addWidget(output_mode_label)

        # Output Mode dropdown
        self.output_mode_dropdown = QComboBox(self)
        self.output_mode_dropdown.addItems(["Total Count", "Breakdown"])
        self.output_mode_dropdown.setStyleSheet(self.COMBOBOX_STYLE)
        self.output_mode_dropdown.currentIndexChanged.connect(self.on_output_mode_changed)
        left_layout.addWidget(self.output_mode_dropdown)

        # Primary Key label
        primary_key_label = QLabel("Primary Key:", self)
        primary_key_label.setStyleSheet("font-weight: bold; color: #212121;")
        left_layout.addWidget(primary_key_label)

        # Primary Key dropdown
        self.primary_key_dropdown = QComboBox(self)
        self.primary_key_dropdown.setStyleSheet(self.COMBOBOX_STYLE)
        self.primary_key_dropdown.currentIndexChanged.connect(self.on_primary_key_changed)
        left_layout.addWidget(self.primary_key_dropdown)

        # Primary Key Value label
        self.primary_key_value_label = QLabel("Value:", self)
        self.primary_key_value_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #212121;
                margin-top: 10px;
            }
        """)
        left_layout.addWidget(self.primary_key_value_label)

        # Primary Key Value input (text box)
        self.primary_key_value_input = QLineEdit(self)
        self.primary_key_value_input.setPlaceholderText("Enter value...")
        self.primary_key_value_input.setStyleSheet(self.LINEEDIT_STYLE)
        left_layout.addWidget(self.primary_key_value_input)

        # Age range inputs (hidden by default, shown for age fields)
        age_range_label = QLabel("Age Range:", self)
        age_range_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #212121;
                margin-top: 10px;
            }
        """)
        age_range_label.hide()
        self.primary_age_range_label = age_range_label
        left_layout.addWidget(age_range_label)

        age_range_layout = QHBoxLayout()
        age_range_layout.setSpacing(10)
        
        self.primary_min_age_input = QSpinBox(self)
        self.primary_min_age_input.setMinimum(0)
        self.primary_min_age_input.setMaximum(150)
        self.primary_min_age_input.setValue(0)
        self.primary_min_age_input.setPrefix("Min: ")
        self.primary_min_age_input.setSuffix(" years")
        self.primary_min_age_input.setStyleSheet(self.SPINBOX_STYLE)
        self.primary_min_age_input.hide()
        age_range_layout.addWidget(self.primary_min_age_input)

        self.primary_max_age_input = QSpinBox(self)
        self.primary_max_age_input.setMinimum(0)
        self.primary_max_age_input.setMaximum(150)
        self.primary_max_age_input.setValue(150)
        self.primary_max_age_input.setPrefix("Max: ")
        self.primary_max_age_input.setSuffix(" years")
        self.primary_max_age_input.setStyleSheet(self.SPINBOX_STYLE)
        self.primary_max_age_input.hide()
        age_range_layout.addWidget(self.primary_max_age_input)

        left_layout.addLayout(age_range_layout)

        # Date Range Type label
        date_range_type_label = QLabel("Date Range Type:", self)
        date_range_type_label.setStyleSheet("font-weight: bold; color: #212121;")
        left_layout.addWidget(date_range_type_label)

        # Date range type selection dropdown
        self.date_range_type_dropdown = QComboBox(self)
        self.date_range_type_dropdown.addItems(["Date of Event", "Date of Registration"])
        self.date_range_type_dropdown.setStyleSheet(self.COMBOBOX_STYLE)
        self.date_range_type_dropdown.currentIndexChanged.connect(self.update_date_range_visibility)
        left_layout.addWidget(self.date_range_type_dropdown)

        # Date range label
        self.date_label = QLabel("Date of Event Range:", self)
        self.date_label.setStyleSheet("""
            QLabel {
                font-size: 12px;                font-weight: bold;                font-weight: bold;
                color: #212121;
                margin-top: 10px;
            }
        """)
        left_layout.addWidget(self.date_label)
        
        self.start_date_input = QDateEdit(self)
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_input.setStyleSheet(date_picker_style)
        left_layout.addWidget(self.start_date_input)

        self.end_date_input = QDateEdit(self)
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDate(QDate.currentDate())
        self.end_date_input.setStyleSheet(date_picker_style)
        left_layout.addWidget(self.end_date_input)

        # Registration date range
        self.reg_date_label = QLabel("Registration Date Range:", self)
        self.reg_date_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #212121;
                margin-top: 10px;
            }
        """)
        left_layout.addWidget(self.reg_date_label)
        
        self.reg_start_date_input = QDateEdit(self)
        self.reg_start_date_input.setCalendarPopup(True)
        self.reg_start_date_input.setDate(QDate.currentDate().addMonths(-1))
        self.reg_start_date_input.setStyleSheet(date_picker_style)
        left_layout.addWidget(self.reg_start_date_input)

        self.reg_end_date_input = QDateEdit(self)
        self.reg_end_date_input.setCalendarPopup(True)
        self.reg_end_date_input.setDate(QDate.currentDate())
        self.reg_end_date_input.setStyleSheet(date_picker_style)
        left_layout.addWidget(self.reg_end_date_input)

        # Secondary Filter section
        secondary_label = QLabel("Secondary Filter (Optional):", self)
        secondary_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #212121;
                margin-top: 10px;
                font-weight: bold;
            }
        """)
        left_layout.addWidget(secondary_label)

        # Secondary filter key dropdown
        self.secondary_filter_key_dropdown = QComboBox(self)
        self.secondary_filter_key_dropdown.setStyleSheet(self.COMBOBOX_STYLE)
        self.secondary_filter_key_dropdown.currentIndexChanged.connect(self.on_secondary_filter_key_changed)
        left_layout.addWidget(self.secondary_filter_key_dropdown)

        # Secondary filter value label
        self.secondary_filter_value_label = QLabel("Value:", self)
        self.secondary_filter_value_label.setStyleSheet("""
            QLabel {
                font-size: 12px;                font-weight: bold;                color: #212121;
                margin-top: 5px;
            }
        """)
        left_layout.addWidget(self.secondary_filter_value_label)

        # Secondary filter value input
        self.secondary_filter_value_input = QLineEdit(self)
        self.secondary_filter_value_input.setPlaceholderText("Enter value...")
        self.secondary_filter_value_input.setStyleSheet(self.LINEEDIT_STYLE)
        left_layout.addWidget(self.secondary_filter_value_input)

        # Secondary age range inputs (hidden by default, shown for age fields)
        secondary_age_range_label = QLabel("Age Range:", self)
        secondary_age_range_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #212121;
                margin-top: 10px;
            }
        """)
        secondary_age_range_label.hide()
        self.secondary_age_range_label = secondary_age_range_label
        left_layout.addWidget(secondary_age_range_label)

        secondary_age_range_layout = QHBoxLayout()
        secondary_age_range_layout.setSpacing(10)
        
        self.secondary_min_age_input = QSpinBox(self)
        self.secondary_min_age_input.setMinimum(0)
        self.secondary_min_age_input.setMaximum(150)
        self.secondary_min_age_input.setValue(0)
        self.secondary_min_age_input.setPrefix("Min: ")
        self.secondary_min_age_input.setSuffix(" years")
        self.secondary_min_age_input.setStyleSheet(self.SPINBOX_STYLE)
        self.secondary_min_age_input.hide()
        secondary_age_range_layout.addWidget(self.secondary_min_age_input)

        self.secondary_max_age_input = QSpinBox(self)
        self.secondary_max_age_input.setMinimum(0)
        self.secondary_max_age_input.setMaximum(150)
        self.secondary_max_age_input.setValue(150)
        self.secondary_max_age_input.setPrefix("Max: ")
        self.secondary_max_age_input.setSuffix(" years")
        self.secondary_max_age_input.setStyleSheet(self.SPINBOX_STYLE)
        self.secondary_max_age_input.hide()
        secondary_age_range_layout.addWidget(self.secondary_max_age_input)

        left_layout.addLayout(secondary_age_range_layout)

        # Buttons
        generate_btn = QPushButton("Generate Statistics", self)
        generate_btn.clicked.connect(self.generate_statistics)
        generate_btn.setStyleSheet(button_style)
        left_layout.addWidget(generate_btn)

        export_pdf_btn = QPushButton("Export Report as PDF", self)
        export_pdf_btn.clicked.connect(self.export_pdf_report)
        export_pdf_btn.setStyleSheet(button_style)
        left_layout.addWidget(export_pdf_btn)

        # Result display area
        result_label = QLabel("Result:", self)
        result_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #212121;
                margin-top: 20px;
            }
        """)
        left_layout.addWidget(result_label)

        # Use a scrollable read-only text area for long outputs
        self.result_display = QTextEdit("Ready", self)
        self.result_display.setReadOnly(True)
        self.result_display.setStyleSheet("""
            QTextEdit {
                font-size: 12px;
                color: #212121;
                padding: 10px;
                border: 1px solid #D1D0D0;
                border-radius: 4px;
                background-color: #FAFAFA;
                min-height: 100px;
                max-height: 200px;
            }
        """)
        left_layout.addWidget(self.result_display)

        # Add spacer to push content to top
        left_layout.addStretch()

        main_layout.addLayout(left_layout)
        self.setLayout(main_layout)

        # Initialize dropdowns
        self.on_record_type_changed()
        self.on_output_mode_changed()
        self.update_date_range_visibility()

    def on_record_type_changed(self):
        """Handle record type selection change."""
        self.on_output_mode_changed()  # Re-populate primary key based on new record type

    def on_output_mode_changed(self):
        """Handle output mode selection change."""
        record_type = self.record_type_dropdown.currentText()
        output_mode = self.output_mode_dropdown.currentText()
        
        # Populate primary key dropdown based on output mode and record type
        self.primary_key_dropdown.blockSignals(True)
        self.primary_key_dropdown.clear()
        
        if output_mode == "Breakdown":
            keys = self.BREAKDOWN_KEYS.get(record_type, [])
        else:  # Total Count
            keys = self.TOTAL_COUNT_KEYS.get(record_type, [])
        
        self.primary_key_dropdown.addItems(keys)
        self.primary_key_dropdown.blockSignals(False)
        
        # Update secondary filter dropdown based on record type
        self.update_secondary_filter_keys()
        
        # Update visibility of primary key value inputs
        self.on_primary_key_changed()

    def on_primary_key_changed(self):
        """Handle primary key selection change."""
        primary_key = self.primary_key_dropdown.currentText()
        output_mode = self.output_mode_dropdown.currentText()
        
        # Determine if we should show value input based on output mode
        is_total_count_mode = (output_mode == "Total Count")
        is_age_field = "age" in primary_key.lower()
        is_all_key = (primary_key == "All")
        
        # Hide value inputs in Breakdown mode or if "All" is selected
        if not is_total_count_mode or is_all_key:
            self.primary_key_value_label.hide()
            self.primary_key_value_input.hide()
            self.primary_age_range_label.hide()
            self.primary_min_age_input.hide()
            self.primary_max_age_input.hide()
        else:
            # Show appropriate input for Total Count mode
            self.primary_key_value_label.show()
            if is_age_field:
                self.primary_key_value_input.hide()
                self.primary_age_range_label.show()
                self.primary_min_age_input.show()
                self.primary_max_age_input.show()
            else:
                self.primary_key_value_input.show()
                self.primary_age_range_label.hide()
                self.primary_min_age_input.hide()
                self.primary_max_age_input.hide()
        
        # Update secondary filter dropdown to disable the selected primary key
        self.update_secondary_filter_keys()

    def on_secondary_filter_key_changed(self):
        """Handle secondary filter key selection change."""
        secondary_key = self.secondary_filter_key_dropdown.currentText()
        is_age_field = "age" in secondary_key.lower()
        is_no_filter = (secondary_key == "None")
        
        # Show/hide secondary filter value inputs based on key type
        if is_no_filter:
            self.secondary_filter_value_label.hide()
            self.secondary_filter_value_input.hide()
            self.secondary_age_range_label.hide()
            self.secondary_min_age_input.hide()
            self.secondary_max_age_input.hide()
        else:
            if is_age_field:
                self.secondary_filter_value_input.hide()
                self.secondary_age_range_label.show()
                self.secondary_min_age_input.show()
                self.secondary_max_age_input.show()
            else:
                self.secondary_filter_value_input.show()
                self.secondary_age_range_label.hide()
                self.secondary_min_age_input.hide()
                self.secondary_max_age_input.hide()
            self.secondary_filter_value_label.show()

    def update_secondary_filter_keys(self):
        """Update secondary filter dropdown, excluding the primary key."""
        record_type = self.record_type_dropdown.currentText()
        primary_key = self.primary_key_dropdown.currentText()
        
        # Get available secondary filter keys
        all_secondary_keys = self.SECONDARY_FILTER_KEYS.get(record_type, [])
        
        # Filter out the primary key if it's not "All"
        available_keys = [k for k in all_secondary_keys if k != primary_key]
        
        self.secondary_filter_key_dropdown.blockSignals(True)
        current_selection = self.secondary_filter_key_dropdown.currentText()
        self.secondary_filter_key_dropdown.clear()
        self.secondary_filter_key_dropdown.addItems(available_keys)
        
        # Try to restore previous selection if it's still available
        if current_selection in available_keys:
            self.secondary_filter_key_dropdown.setCurrentText(current_selection)
        
        self.secondary_filter_key_dropdown.blockSignals(False)
        self.on_secondary_filter_key_changed()

    def update_date_range_visibility(self):
        """Show/hide date range inputs based on selected date range type."""
        date_range_type = self.date_range_type_dropdown.currentText()
        
        if date_range_type == "Date of Event":
            # Show event date range, hide registration date range
            self.date_label.show()
            self.start_date_input.show()
            self.end_date_input.show()
            self.reg_date_label.hide()
            self.reg_start_date_input.hide()
            self.reg_end_date_input.hide()
        else:  # Date of Registration
            # Hide event date range, show registration date range
            self.date_label.hide()
            self.start_date_input.hide()
            self.end_date_input.hide()
            self.reg_date_label.show()
            self.reg_start_date_input.show()
            self.reg_end_date_input.show()
    
    def _get_table_and_date_field(self, record_type):
        """Get database table and date field name for a record type."""
        table_map = {
            "Live Birth": ("birth_index", "date_of_birth"),
            "Death": ("death_index", "date_of_death"),
            "Marriage": ("marriage_index", "date_of_marriage")
        }
        return table_map.get(record_type, ("birth_index", "date_of_birth"))

    def generate_statistics(self):
        """Generate statistics based on output mode (Breakdown or Total Count)."""
        record_type = self.record_type_dropdown.currentText()
        output_mode = self.output_mode_dropdown.currentText()
        primary_key = self.primary_key_dropdown.currentText()
        date_range_type = self.date_range_type_dropdown.currentText()
        
        # Get date range (event vs registration)
        if date_range_type == "Date of Event":
            start_date = self.start_date_input.date().toString("yyyy-MM-dd")
            end_date = self.end_date_input.date().toString("yyyy-MM-dd")
            # registration date range not active
            reg_start_date = None
            reg_end_date = None
        else:  # Date of Registration
            start_date = self.reg_start_date_input.date().toString("yyyy-MM-dd")
            end_date = self.reg_end_date_input.date().toString("yyyy-MM-dd")
            # when Date of Registration is selected, make registration range available
            reg_start_date = self.reg_start_date_input.date().toString("yyyy-MM-dd")
            reg_end_date = self.reg_end_date_input.date().toString("yyyy-MM-dd")
        
        # Get primary key value (for Total Count mode)
        primary_key_value = None
        primary_min_age = None
        primary_max_age = None
        if output_mode == "Total Count" and primary_key != "All":
            if "age" in primary_key.lower():
                primary_min_age = self.primary_min_age_input.value()
                primary_max_age = self.primary_max_age_input.value()
            else:
                primary_key_value = self.primary_key_value_input.text().strip()
        
        # Get secondary filter
        secondary_filter_key = self.secondary_filter_key_dropdown.currentText()
        secondary_filter_value = None
        secondary_min_age = None
        secondary_max_age = None
        
        if secondary_filter_key != "None":
            if "age" in secondary_filter_key.lower():
                secondary_min_age = self.secondary_min_age_input.value()
                secondary_max_age = self.secondary_max_age_input.value()
            else:
                secondary_filter_value = self.secondary_filter_value_input.text().strip()
        
        conn = self.create_connection()
        try:
            cursor = conn.cursor()
            table, date_field = self._get_table_and_date_field(record_type)
            
            # Validate date field
            if not all(c.isalnum() or c == '_' for c in date_field):
                QMessageBox.critical(self, "Security Error", "Invalid date field")
                return
            
            # Determine which date field to use for filtering
            use_registration_date = (date_range_type == "Date of Registration")
            active_date_field = "date_of_reg" if use_registration_date else date_field
            
            if output_mode == "Breakdown":
                # Breakdown mode: show distinct values and their counts
                results = self._generate_breakdown(
                    cursor, table, active_date_field, primary_key,
                    secondary_filter_key, record_type,
                    start_date, end_date, reg_start_date, reg_end_date,
                    secondary_filter_value, secondary_min_age, secondary_max_age
                )
                
                if results:
                    AuditLogger.log_action(
                        conn, self.current_user, "STATISTICS_GENERATED",
                        {"mode": "breakdown", "record_type": record_type, "key": primary_key,
                         "result_count": len(results), "start_date": start_date, "end_date": end_date}
                    )
                    conn.commit()
                    self._display_breakdown_results(results, primary_key)
                else:
                    AuditLogger.log_action(
                        conn, self.current_user, "STATISTICS_NO_DATA",
                        {"mode": "breakdown", "record_type": record_type, "key": primary_key}
                    )
                    conn.commit()
                    self.result_display.setPlainText("No data found for the selected criteria.")
            else:  # Total Count mode
                # Total count mode: count records based on filters
                total_count = self._generate_total_count(
                    cursor, table, active_date_field, primary_key,
                    secondary_filter_key, record_type,
                    start_date, end_date, reg_start_date, reg_end_date,
                    primary_key_value, primary_min_age, primary_max_age,
                    secondary_filter_value, secondary_min_age, secondary_max_age
                )
                
                if total_count >= 0:
                    AuditLogger.log_action(
                        conn, self.current_user, "STATISTICS_GENERATED",
                        {"mode": "total_count", "record_type": record_type, "key": primary_key,
                         "count": total_count, "start_date": start_date, "end_date": end_date}
                    )
                    conn.commit()
                    self._display_total_count_result(primary_key, primary_key_value, total_count, primary_min_age, primary_max_age)
                else:
                    self.result_display.setPlainText("Error generating statistics.")
        
        except psycopg2.Error as e:
            AuditLogger.log_action(
                conn, self.current_user, "DATABASE_ERROR",
                {"operation": "generate_statistics", "error": str(e)}
            )
            conn.commit()
            QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")
            self.result_display.setPlainText("Error")
        
        finally:
            self.closeConnection()

    def _generate_breakdown(self, cursor, table, date_field, primary_key, secondary_filter_key, 
                           record_type, start_date, end_date, reg_start_date=None, reg_end_date=None,
                           secondary_filter_value=None, secondary_min_age=None, secondary_max_age=None):
        """Generate breakdown statistics for a key."""
        try:
            if primary_key == "All":
                # Total count for the record type
                base_where = f'DATE("{date_field}") BETWEEN %s::date AND %s::date'
                params = [start_date, end_date]
                query = f'SELECT COUNT(*) as count FROM "{table}" WHERE {base_where}'
            elif primary_key == "Monthly Totals":
                base_where = f'DATE("{date_field}") BETWEEN %s::date AND %s::date'
                params = [start_date, end_date]
                query = (
                    f'SELECT date_trunc(\'month\', "{date_field}") AS month, '
                    f'COUNT(*) as count FROM "{table}" WHERE {base_where}'
                )
            elif primary_key == "Legitimate":
                base_where = f'DATE("{date_field}") BETWEEN %s::date AND %s::date'
                params = [start_date, end_date]
                query = (
                    f"SELECT CASE "
                    f"WHEN parents_marriage_date IS NULL THEN 'ILLEGITIMATE' "
                    f"ELSE 'LEGITIMATE' END AS legitimacy, "
                    f'COUNT(*) as count FROM "{table}" WHERE {base_where}'
                )
            elif primary_key in self.AGE_RANGE_BREAKDOWN_KEYS:
                base_where = f'DATE("{date_field}") BETWEEN %s::date AND %s::date'
                params = [start_date, end_date]

                age_column_map = {
                    "Mother Age (Youngest/Oldest)": "mother_age",
                    "Father Age (Youngest/Oldest)": "father_age",
                    "Age (Youngest/Oldest)": "age_years",
                    "Husband Age (Youngest/Oldest)": "husband_age",
                    "Wife Age (Youngest/Oldest)": "wife_age",
                }
                age_column = age_column_map.get(primary_key)
                if not age_column or not all(c.isalnum() or c == '_' for c in age_column):
                    return None

                base_where += f' AND "{age_column}" IS NOT NULL'
                query = (
                    f'SELECT MIN("{age_column}") as min_age, MAX("{age_column}") as max_age '
                    f'FROM "{table}" WHERE {base_where}'
                )
            else:
                # Breakdown by primary key
                primary_column = self.KEY_COLUMN_MAP.get(primary_key)
                if not primary_column or not all(c.isalnum() or c == '_' for c in primary_column):
                    return None
                
                base_where = f'DATE("{date_field}") BETWEEN %s::date AND %s::date'
                params = [start_date, end_date]
                
                # Add primary key filter (only for non-null values)
                base_where += f' AND "{primary_column}" IS NOT NULL'
                query = f'SELECT "{primary_column}", COUNT(*) as count FROM "{table}" WHERE {base_where}'
            
            # Add secondary filter if present
            if secondary_filter_key != "None":
                secondary_column = self.KEY_COLUMN_MAP.get(secondary_filter_key)
                if secondary_column and all(c.isalnum() or c == '_' for c in secondary_column):
                    if "age" in secondary_filter_key.lower():
                        query = query.replace("WHERE", f'WHERE "{secondary_column}" BETWEEN %s AND %s AND')
                        params.insert(-len([start_date, end_date]), secondary_min_age)
                        params.insert(-len([start_date, end_date]) + 1, secondary_max_age)
                    # Special handling for composite residence filters
                    elif secondary_filter_key == "SoLeyte Residents (Excl. Maasin)":
                        query = query.replace("WHERE", f'WHERE "soleyte_resident" = TRUE AND "maasin_resident" = FALSE AND')
                    elif secondary_filter_key == "Residents outside Leyte":
                        query = query.replace("WHERE", f'WHERE "maasin_resident" = FALSE AND "soleyte_resident" = FALSE AND "leyte_resident" = FALSE AND')
                    # Boolean column handling (Late Registration, resident filters)
                    elif secondary_filter_key == "Late Registration" or "resident" in secondary_filter_key.lower():
                        query = query.replace("WHERE", f'WHERE "{secondary_column}" = TRUE AND')
                    else:
                        # Use regex whole-word match for name fields, otherwise use ILIKE
                        if "name" in secondary_filter_key.lower():
                            pattern = '\\y' + re.escape(secondary_filter_value) + '\\y'
                            query = query.replace("WHERE", f'WHERE "{secondary_column}" ~* %s AND')
                            params.insert(-len([start_date, end_date]), pattern)
                        else:
                            query = query.replace("WHERE", f'WHERE "{secondary_column}" ILIKE %s AND')
                            params.insert(-len([start_date, end_date]), f'%{secondary_filter_value}%')
            
            # Add GROUP BY for non-All case
            if primary_key != "All":
                if primary_key == "Monthly Totals":
                    query += " GROUP BY month ORDER BY month ASC"
                elif primary_key == "Legitimate":
                    query += " GROUP BY legitimacy ORDER BY count DESC"
                elif primary_key in self.AGE_RANGE_BREAKDOWN_KEYS:
                    # MIN/MAX query: no grouping or ordering needed
                    pass
                else:
                    primary_column = self.KEY_COLUMN_MAP.get(primary_key)
                    query += f' GROUP BY "{primary_column}" ORDER BY count DESC'
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            if primary_key == "All":
                # Convert single total to list format
                return [(None, results[0][0])] if results else []
            if primary_key in self.AGE_RANGE_BREAKDOWN_KEYS:
                min_age, max_age = results[0] if results else (None, None)
                return [("Youngest", min_age), ("Oldest", max_age)]
            return results
        
        except Exception as e:
            print(f"Error in _generate_breakdown: {e}")
            return None

    def _generate_total_count(self, cursor, table, date_field, primary_key, secondary_filter_key,
                             record_type, start_date, end_date, reg_start_date=None, reg_end_date=None,
                             primary_key_value=None, primary_min_age=None, primary_max_age=None,
                             secondary_filter_value=None, secondary_min_age=None, secondary_max_age=None):
        """Generate total count statistics with legacy query rules."""
        try:
            # Standard filtering
            base_where = f'DATE("{date_field}") BETWEEN %s::date AND %s::date'
            params = [start_date, end_date]

            # Add primary key filter if not "All"
            if primary_key != "All":
                primary_column = self.KEY_COLUMN_MAP.get(primary_key)
                if not primary_column or not all(c.isalnum() or c == '_' for c in primary_column):
                    return -1

                # Age range handling
                if "age" in primary_key.lower():
                    base_where += f' AND "{primary_column}" BETWEEN %s AND %s'
                    params.extend([primary_min_age, primary_max_age])
                # Special handling for mixed residence filters
                elif primary_key == "SoLeyte Residents (Excl. Maasin)":
                    base_where += f' AND "soleyte_resident" = TRUE AND "maasin_resident" = FALSE'
                elif primary_key == "Residents outside Leyte":
                    base_where += f' AND "maasin_resident" = FALSE AND "soleyte_resident" = FALSE AND "leyte_resident" = FALSE'
                # Boolean column handling (Late Registration, resident filters)
                elif primary_key == "Late Registration" or "resident" in primary_key.lower():
                    base_where += f' AND "{primary_column}" = TRUE'
                else:
                    # Handle name fields and specific text fields per legacy rules
                    name_fields = {
                        "Live Birth": ["Name", "Name of Mother", "Name of Father"],
                        "Death": ["Name"],
                        "Marriage": ["Husband Name", "Wife Name"]
                    }
                    if record_type in name_fields and primary_key in name_fields[record_type]:
                        pattern = '\\y' + re.escape(primary_key_value) + '\\y'
                        base_where += f' AND "{primary_column}" ~* %s'
                        params.append(pattern)
                    elif primary_key in ["Sex", "Type of Birth", "Civil Status"]:
                        base_where += f' AND "{primary_column}" ILIKE %s'
                        params.append(primary_key_value)
                    else:
                        base_where += f' AND "{primary_column}" ILIKE %s AND "{primary_column}" IS NOT NULL'
                        params.append(f'%{primary_key_value}%')

            # Add secondary filter if present
            if secondary_filter_key != "None":
                secondary_column = self.KEY_COLUMN_MAP.get(secondary_filter_key)
                if secondary_column and all(c.isalnum() or c == '_' for c in secondary_column):
                    if "age" in secondary_filter_key.lower():
                        base_where += f' AND "{secondary_column}" BETWEEN %s AND %s'
                        params.extend([secondary_min_age, secondary_max_age])
                    # Special handling for mixed residence filters
                    elif secondary_filter_key == "SoLeyte Residents (Excl. Maasin)":
                        base_where += f' AND "soleyte_resident" = TRUE AND "maasin_resident" = FALSE'
                    elif secondary_filter_key == "Residents outside Leyte":
                        base_where += f' AND "maasin_resident" = FALSE AND "soleyte_resident" = FALSE AND "leyte_resident" = FALSE'
                    # Boolean column handling (Late Registration, resident filters)
                    elif secondary_filter_key == "Late Registration" or "resident" in secondary_filter_key.lower():
                        base_where += f' AND "{secondary_column}" = TRUE'
                    else:
                        # Name fields use regex whole-word match
                        if "name" in secondary_filter_key.lower():
                            pattern = '\\y' + re.escape(secondary_filter_value) + '\\y'
                            base_where += f' AND "{secondary_column}" ~* %s'
                            params.append(pattern)
                        elif secondary_filter_key in ["Sex", "Type of Birth", "Civil Status"]:
                            base_where += f' AND "{secondary_column}" ILIKE %s'
                            params.append(secondary_filter_value)
                        else:
                            base_where += f' AND "{secondary_column}" ILIKE %s AND "{secondary_column}" IS NOT NULL'
                            params.append(f'%{secondary_filter_value}%')

            query = f'SELECT COUNT(*) FROM "{table}" WHERE {base_where}'
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else 0

        except Exception as e:
            print(f"Error in _generate_total_count: {e}")
            return -1

    def _display_breakdown_results(self, results, key_name):
        """Display breakdown results in the result display widget."""
        if not results:
            self.result_display.setPlainText("No results")
            return
        
        if key_name == "All":
            # Just show total
            total = results[0][1] if results else 0
            text = f"Total {self.record_type_dropdown.currentText()} Records: {total}"
        elif key_name in self.AGE_RANGE_BREAKDOWN_KEYS:
            lines = [f"Breakdown of {key_name}:"]
            for label, age in results:
                display_age = "N/A" if age is None else str(age)
                lines.append(f"  {label}: {display_age}")
            text = "\n".join(lines)
        else:
            # Show breakdown for other keys
            lines = [f"Breakdown of {key_name}:"]
            total = 0
            others_count = 0
            for value, count in results:
                # Late Registration is boolean, show as Late/Timely
                if key_name == "Late Registration":
                    display_value = "Late" if value is True else "Timely" if value is False else "N/A"
                elif key_name == "Monthly Totals":
                    try:
                        display_value = value.strftime("%B")
                    except Exception:
                        display_value = str(value) if value else "N/A"
                elif key_name == "Place of Birth":
                    allowed_places_of_birth = {
                        "SALVACION OPPUS YÑIGUEZ MEMORIAL PROVINCIAL HOSPITAL",
                        "MAASIN MEDCITY HOSPITAL",
                        "LIVINGHOPE HOSPITAL, INC.",
                        "CM MATERNITY CLINIC",
                    }
                    if value in allowed_places_of_birth:
                        display_value = value
                    else:
                        others_count += count
                        total += count
                        continue
                elif key_name == "Place of Death":
                    allowed_places_of_death = {
                        "SALVACION OPPUS YÑIGUEZ MEMORIAL PROVINCIAL HOSPITAL",
                        "MAASIN MEDCITY HOSPITAL",
                        "LIVINGHOPE HOSPITAL, INC.",
                        "CM MATERNITY CLINIC",
                    }
                    if value in allowed_places_of_death:
                        display_value = value
                    else:
                        others_count += count
                        total += count
                        continue
                elif key_name == "Attendant":
                    allowed_attendants = {
                        "PHYSICIAN",
                        "MIDWIFE",
                        "HILOT",
                        "DON'T KNOW",
                        "OTHER HEALTH PRACTITIONER",
                        "NOT ATTENDED",
                        "NOT STATED",
                    }
                    if value in allowed_attendants:
                        display_value = value
                    else:
                        others_count += count
                        total += count
                        continue
                else:
                    display_value = str(value) if value else "N/A"
                lines.append(f"  {display_value}: {count}")
                total += count
            if key_name == "Attendant" and others_count:
                lines.append(f"  OTHERS: {others_count}")
            if key_name in {"Place of Birth", "Place of Death"} and others_count:
                lines.append(f"  AT RESIDENCE OR OTHERS: {others_count}")
            lines.append(f"\nTotal: {total}")
            text = "\n".join(lines)
        
        self.result_display.setPlainText(text)

    def _display_total_count_result(self, key_name, key_value, total_count, min_age=None, max_age=None):
        """Display total count result in the result display widget."""
        if key_name == "All":
            text = f"Total {self.record_type_dropdown.currentText()} Records: {total_count}"
        elif "age" in key_name.lower():
            # For age fields, display the age range
            text = f"{key_name}: {min_age} - {max_age} years\nTotal Count: {total_count}"
        else:
            text = f"{key_name}: {key_value}\nTotal Count: {total_count}"
        
        self.result_display.setPlainText(text)


    def export_pdf_report(self):
        """Export the current statistics result to a PDF file."""
        record_type = self.record_type_dropdown.currentText()
        output_mode = self.output_mode_dropdown.currentText()
        primary_key = self.primary_key_dropdown.currentText()
        date_range_type = self.date_range_type_dropdown.currentText()
        
        # Get the current result text
        result_text = self.result_display.toPlainText()
        if "Ready" in result_text or result_text == "Error":
            QMessageBox.information(self, "Export PDF", "Please generate statistics first before exporting.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "", "PDF Files (*.pdf)")
        if not file_path:
            return
        
        try:
            # Generate simple text-based PDF report
            c = pdf_canvas.Canvas(file_path, pagesize=letter)
            width, height = letter

            # Title
            c.setFont("Helvetica-Bold", 20)
            c.drawString(1 * inch, height - 1 * inch, "Statistics Report")

            # Report details
            y_position = height - 1.5 * inch
            c.setFont("Helvetica", 12)
            c.drawString(1 * inch, y_position, f"Record Type: {record_type}")
            y_position -= 0.3 * inch
            c.drawString(1 * inch, y_position, f"Output Mode: {output_mode}")
            y_position -= 0.3 * inch
            c.drawString(1 * inch, y_position, f"Primary Key: {primary_key}")
            y_position -= 0.3 * inch
            c.drawString(1 * inch, y_position, f"Date Range Type: {date_range_type}")
            y_position -= 0.5 * inch

            # Results
            c.setFont("Helvetica-Bold", 14)
            c.drawString(1 * inch, y_position, "Results:")
            y_position -= 0.3 * inch
            
            c.setFont("Helvetica", 11)
            # Draw the result text, wrapping if needed
            for line in result_text.split('\n'):
                if y_position < 0.5 * inch:
                    c.showPage()
                    y_position = height - 1 * inch
                c.drawString(1 * inch, y_position, line)
                y_position -= 0.25 * inch

            # Footer
            c.setFont("Helvetica", 10)
            c.drawString(1 * inch, 0.5 * inch, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            c.drawString(1 * inch, 0.3 * inch, f"Generated by: {self.current_user}")

            c.save()

            conn = self.create_connection()
            try:
                AuditLogger.log_action(
                    conn, self.current_user, "PDF_EXPORT_SUCCESS",
                    {
                        "record_type": record_type,
                        "output_mode": output_mode,
                        "primary_key": primary_key,
                        "file_path": file_path
                    }
                )
                conn.commit()
            finally:
                self.closeConnection()
            
            QMessageBox.information(self, "Success", f"PDF report exported successfully!")

        except Exception as e:
            conn = self.create_connection()
            try:
                AuditLogger.log_action(
                    conn, self.current_user, "PDF_EXPORT_ERROR",
                    {
                        "error": str(e),
                        "record_type": record_type,
                        "output_mode": output_mode
                    }
                )
                conn.commit()
            finally:
                self.closeConnection()
            
            QMessageBox.critical(self, "Export Error", f"Failed to export PDF: {str(e)}")
    def showEvent(self, event):
        super().showEvent(event)
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_OPENED",
                {"window": "StatisticsWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def closeEvent(self, event):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_CLOSED",
                {"window": "StatisticsWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()
            event.ignore()
            self.hide()