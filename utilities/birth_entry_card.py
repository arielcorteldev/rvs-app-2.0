from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QCheckBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QPalette

from utilities.stylesheets import button_style, date_picker_style, combo_box_style, message_box_style
from utilities.audit_logger import AuditLogger
from utilities.db_config import POSTGRES_CONFIG

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


CHECKBOX_STYLE = """
    QCheckBox::indicator:unchecked {
        background-color: #FFFFFF;
        border: 1px solid #D1D0D0;
    }
    QCheckBox::indicator:unchecked:hover {
        background-color: #F5F5F5;
        border: 1px solid #999999;
    }
    QCheckBox::indicator:checked {
        background-color: #ce305e;
        border: 1px solid #ce305e;
    }
    QCheckBox::indicator:checked:hover {
        background-color: #a8224a;
        border: 1px solid #a8224a;
    }
"""

MARRIAGE_PLACE_NULL_TRIGGERS = ["NOT MARRIED", "FORGOTTEN", "DON'T KNOW", "NOT APPLICABLE"]


class BirthEntryCard(QFrame):
    """A self-contained card widget representing one birth record entry."""

    deleted = Signal(object)  # emits self when deleted, so parent can remove it

    def __init__(self, entry_number, current_user, get_selected_pdf_fn, parent=None):
        super().__init__(parent)
        self.entry_number = entry_number
        self.current_user = current_user
        self.get_selected_pdf = get_selected_pdf_fn  # callable: returns current file_path
        self.record_id = None  # set after saving; used for updates and deletes

        self.connection = None

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #D1D0D0;
                border-radius: 6px;
            }
            QLabel {
                color: #212121;
                border: none;
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
            QComboBox {
                font-weight: bold;
            }
            QDateEdit {
                font-weight: bold;
            }
        """)

        self._build_ui()

    # ------------------------------------------------------------------ #
    #  DB helpers                                                          #
    # ------------------------------------------------------------------ #

    def _create_connection(self):
        if self.connection is None:
            self.connection = psycopg2.connect(**POSTGRES_CONFIG)
            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return self.connection

    def _close_connection(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    # ------------------------------------------------------------------ #
    #  UI helpers                                                          #
    # ------------------------------------------------------------------ #

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setAutoFillBackground(True)
        return lbl

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────── #
        header_layout = QHBoxLayout()
        self.header_label = QLabel(f"Entry #{self.entry_number}")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #ce305e; border: none;")
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        outer.addLayout(header_layout)

        # ── Row 1: Page No, Book No, Registry No ──────────────────────── #
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.page_no_input = QLineEdit()
        self.page_no_input.setPlaceholderText("Page No.")
        self.page_no_input.setFixedWidth(200)
        c = QVBoxLayout(); c.addWidget(self._label("Page No.:")); c.addWidget(self.page_no_input)
        row1.addLayout(c)

        self.book_no_input = QLineEdit()
        self.book_no_input.setPlaceholderText("Book No.")
        self.book_no_input.setFixedWidth(200)
        c = QVBoxLayout(); c.addWidget(self._label("Book No.:")); c.addWidget(self.book_no_input)
        row1.addLayout(c)

        self.reg_no_input = QLineEdit()
        self.reg_no_input.setPlaceholderText("Registry No.")
        self.reg_no_input.setFixedWidth(200)
        c = QVBoxLayout(); c.addWidget(self._label("Registry No.:")); c.addWidget(self.reg_no_input)
        row1.addLayout(c)

        row1.addStretch()
        outer.addLayout(row1)

        # ── Row 2: Name, Sex ──────────────────────────────────────────── #
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        self.name_input.setFixedWidth(420)
        c = QVBoxLayout(); c.addWidget(self._label("Name:")); c.addWidget(self.name_input)
        row2.addLayout(c)

        self.sex_combo = QComboBox()
        self.sex_combo.addItems(["MALE", "FEMALE", "NO ENTRY"])
        self.sex_combo.setFixedWidth(200)
        self.sex_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Sex:")); c.addWidget(self.sex_combo)
        row2.addLayout(c)

        row2.addStretch()
        outer.addLayout(row2)

        # ── Row 3: DOB, Place of Birth, Type of Birth ─────────────────── #
        row3 = QHBoxLayout()
        row3.setSpacing(10)

        dob_col = QVBoxLayout()
        dob_lbl_row = QHBoxLayout()
        dob_lbl_row.setSpacing(5)
        dob_lbl_row.addWidget(self._label("Date of Birth:"))
        self.has_dob_check = QCheckBox("Has Date")
        self.has_dob_check.setChecked(True)
        self.has_dob_check.setStyleSheet(CHECKBOX_STYLE)
        self.has_dob_check.stateChanged.connect(
            lambda: self.date_of_birth_input.setEnabled(self.has_dob_check.isChecked())
        )
        dob_lbl_row.addWidget(self.has_dob_check)
        dob_lbl_row.addStretch()
        dob_col.addLayout(dob_lbl_row)
        self.date_of_birth_input = QDateEdit()
        self.date_of_birth_input.setCalendarPopup(True)
        self.date_of_birth_input.setDate(QDate.currentDate())
        self.date_of_birth_input.setFixedWidth(150)
        self.date_of_birth_input.setStyleSheet(date_picker_style)
        dob_col.addWidget(self.date_of_birth_input)
        row3.addLayout(dob_col)

        self.place_of_birth_combo = QComboBox()
        self.place_of_birth_combo.setEditable(True)
        self.place_of_birth_combo.addItems([
            "SALVACION OPPUS YÑIGUEZ MEMORIAL PROVINCIAL HOSPITAL",
            "MAASIN MEDCITY HOSPITAL",
            "LIVINGHOPE HOSPITAL, INC.",
            "CM MATERNITY CLINIC",
            "NO ENTRY",
        ])
        self.place_of_birth_combo.setFixedWidth(370)
        self.place_of_birth_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Place of Birth:")); c.addWidget(self.place_of_birth_combo)
        row3.addLayout(c)

        self.type_of_birth_combo = QComboBox()
        self.type_of_birth_combo.addItems([
            "SINGLE", "TWIN", "TRIPLET", "QUADRUPLET", "QUINTUPLET",
            "SEXTUPLET", "SEPTUPLET", "OCTUPLET", "NONUPLET", "DECAPLET", "NO ENTRY"
        ])
        self.type_of_birth_combo.setFixedWidth(110)
        self.type_of_birth_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Type of Birth:")); c.addWidget(self.type_of_birth_combo)
        row3.addLayout(c)

        row3.addStretch()
        outer.addLayout(row3)

        # ── Row 4: Mother Name, Nationality, Age ──────────────────────── #
        row4 = QHBoxLayout()
        row4.setSpacing(10)

        self.mother_name_input = QLineEdit()
        self.mother_name_input.setPlaceholderText("Name of Mother")
        self.mother_name_input.setFixedWidth(320)
        c = QVBoxLayout(); c.addWidget(self._label("Name of Mother:")); c.addWidget(self.mother_name_input)
        row4.addLayout(c)

        self.mother_nationality_combo = QComboBox()
        self.mother_nationality_combo.setEditable(True)
        self.mother_nationality_combo.addItems([
            "FILIPINO", "CHINESE", "INDIAN", "AMERICAN", "JAPANESE",
            "SOUTH KOREAN", "GERMAN", "AUSTRALIAN", "TAIWANESE",
            "INDONESIAN", "VIETNAMESE", "NO ENTRY"
        ])
        self.mother_nationality_combo.setFixedWidth(200)
        self.mother_nationality_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Nationality of Mother:")); c.addWidget(self.mother_nationality_combo)
        row4.addLayout(c)

        self.mother_age_input = QLineEdit()
        self.mother_age_input.setPlaceholderText("Age")
        self.mother_age_input.setFixedWidth(80)
        c = QVBoxLayout(); c.addWidget(self._label("Age of Mother:")); c.addWidget(self.mother_age_input)
        row4.addLayout(c)

        row4.addStretch()
        outer.addLayout(row4)

        # ── Row 5: Resident combos ─────────────────────────────────────── #
        row5 = QHBoxLayout()
        row5.setSpacing(10)

        self.maasin_resident_combo = QComboBox()
        self.maasin_resident_combo.addItems(["NO", "YES", "NO ENTRY"])
        self.maasin_resident_combo.setFixedWidth(140)
        self.maasin_resident_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Maasin Resident:")); c.addWidget(self.maasin_resident_combo)
        row5.addLayout(c)

        self.soleyte_resident_combo = QComboBox()
        self.soleyte_resident_combo.addItems(["NO", "YES", "NO ENTRY"])
        self.soleyte_resident_combo.setFixedWidth(140)
        self.soleyte_resident_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Soleyte Resident:")); c.addWidget(self.soleyte_resident_combo)
        row5.addLayout(c)

        self.leyte_resident_combo = QComboBox()
        self.leyte_resident_combo.addItems(["NO", "YES", "NO ENTRY"])
        self.leyte_resident_combo.setFixedWidth(140)
        self.leyte_resident_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Leyte Resident:")); c.addWidget(self.leyte_resident_combo)
        row5.addLayout(c)

        row5.addStretch()
        outer.addLayout(row5)

        # ── Row 6: Father Name, Nationality, Age ──────────────────────── #
        row6 = QHBoxLayout()
        row6.setSpacing(10)

        self.father_name_input = QLineEdit()
        self.father_name_input.setPlaceholderText("Name of Father")
        self.father_name_input.setFixedWidth(320)
        c = QVBoxLayout(); c.addWidget(self._label("Name of Father:")); c.addWidget(self.father_name_input)
        row6.addLayout(c)

        self.father_nationality_combo = QComboBox()
        self.father_nationality_combo.setEditable(True)
        self.father_nationality_combo.addItems([
            "FILIPINO", "CHINESE", "INDIAN", "AMERICAN", "JAPANESE",
            "SOUTH KOREAN", "GERMAN", "AUSTRALIAN", "TAIWANESE",
            "INDONESIAN", "VIETNAMESE", "NO ENTRY"
        ])
        self.father_nationality_combo.setFixedWidth(200)
        self.father_nationality_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Nationality of Father:")); c.addWidget(self.father_nationality_combo)
        row6.addLayout(c)

        self.father_age_input = QLineEdit()
        self.father_age_input.setPlaceholderText("Age")
        self.father_age_input.setFixedWidth(80)
        c = QVBoxLayout(); c.addWidget(self._label("Age of Father:")); c.addWidget(self.father_age_input)
        row6.addLayout(c)

        row6.addStretch()
        outer.addLayout(row6)

        # ── Row 7: Place of Marriage, Date of Marriage ────────────────── #
        row7 = QHBoxLayout()
        row7.setSpacing(10)

        self.marriage_place_input = QComboBox()
        self.marriage_place_input.setEditable(True)
        self.marriage_place_input.addItems([
            "NOT MARRIED", "FORGOTTEN", "DON'T KNOW", "NOT APPLICABLE",
            "MAASIN CITY, SOUTHERN LEYTE", "MACROHON, SOUTHERN LEYTE",
            "PADRE BURGOS, SOUTHERN LEYTE", "MALITBOG, SOUTHERN LEYTE",
            "TOMAS OPPUS, SOUTHERN LEYTE", "BONTOC, SOUTHERN LEYTE",
            "SOGOD, SOUTHERN LEYTE", "LIBAGON, SOUTHERN LEYTE",
            "LILOAN, SOUTHERN LEYTE", "SAN FRANCISCO, SOUTHERN LEYTE",
            "PINTUYAN, SOUTHERN LEYTE", "SAN RICARDO, SOUTHERN LEYTE",
            "SAINT BERNARD, SOUTHERN LEYTE", "SAN JUAN, SOUTHERN LEYTE",
            "ANAHAWAN, SOUTHERN LEYTE", "HINUNDAYAN, SOUTHERN LEYTE",
            "HINUNANGAN, SOUTHERN LEYTE", "SILAGO, SOUTHERN LEYTE",
            "LIMASAWA, SOUTHERN LEYTE", "MATALOM, LEYTE",
            "BATO, LEYTE", "HILONGOS, LEYTE", "NO ENTRY"
        ])
        self.marriage_place_input.setFixedWidth(420)
        self.marriage_place_input.setStyleSheet(combo_box_style)
        self.marriage_place_input.currentTextChanged.connect(self._handle_marriage_place_change)
        c = QVBoxLayout(); c.addWidget(self._label("Place of Marriage:")); c.addWidget(self.marriage_place_input)
        row7.addLayout(c)

        dom_col = QVBoxLayout()
        dom_lbl_row = QHBoxLayout()
        dom_lbl_row.setSpacing(5)
        dom_lbl_row.addWidget(self._label("Date of Marriage:"))
        self.has_dom_check = QCheckBox("Has Date")
        self.has_dom_check.setChecked(True)
        self.has_dom_check.setStyleSheet(CHECKBOX_STYLE)
        self.has_dom_check.stateChanged.connect(
            lambda: self.date_of_marriage_input.setEnabled(self.has_dom_check.isChecked())
        )
        dom_lbl_row.addWidget(self.has_dom_check)
        dom_lbl_row.addStretch()
        dom_col.addLayout(dom_lbl_row)
        self.date_of_marriage_input = QDateEdit()
        self.date_of_marriage_input.setCalendarPopup(True)
        self.date_of_marriage_input.setDate(QDate.currentDate())
        self.date_of_marriage_input.setFixedWidth(200)
        self.date_of_marriage_input.setStyleSheet(date_picker_style)
        dom_col.addWidget(self.date_of_marriage_input)
        row7.addLayout(dom_col)

        row7.addStretch()
        outer.addLayout(row7)

        # ── Row 8: Attendant, Late Reg, Date of Reg ───────────────────── #
        row8 = QHBoxLayout()
        row8.setSpacing(10)

        self.attendant_combo = QComboBox()
        self.attendant_combo.setEditable(True)
        self.attendant_combo.addItems([
            "PHYSICIAN", "MIDWIFE", "NURSE", "HILOT",
            "OTHERS", "NOT APPLICABLE", "DON'T KNOW", "NO ENTRY"
        ])
        self.attendant_combo.setFixedWidth(150)
        self.attendant_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Attendant:")); c.addWidget(self.attendant_combo)
        row8.addLayout(c)

        self.late_reg_combo = QComboBox()
        self.late_reg_combo.addItems(["NO", "YES", "NO ENTRY"])
        self.late_reg_combo.setFixedWidth(140)
        self.late_reg_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Late Registration:")); c.addWidget(self.late_reg_combo)
        row8.addLayout(c)

        dor_col = QVBoxLayout()
        dor_lbl_row = QHBoxLayout()
        dor_lbl_row.setSpacing(5)
        dor_lbl_row.addWidget(self._label("Date of Registration:"))
        self.has_dor_check = QCheckBox("Has Date")
        self.has_dor_check.setChecked(True)
        self.has_dor_check.setStyleSheet(CHECKBOX_STYLE)
        self.has_dor_check.stateChanged.connect(
            lambda: self.date_of_reg_input.setEnabled(self.has_dor_check.isChecked())
        )
        dor_lbl_row.addWidget(self.has_dor_check)
        dor_lbl_row.addStretch()
        dor_col.addLayout(dor_lbl_row)
        self.date_of_reg_input = QDateEdit()
        self.date_of_reg_input.setCalendarPopup(True)
        self.date_of_reg_input.setDate(QDate.currentDate())
        self.date_of_reg_input.setFixedWidth(150)
        self.date_of_reg_input.setStyleSheet(date_picker_style)
        dor_col.addWidget(self.date_of_reg_input)
        row8.addLayout(dor_col)

        row8.addStretch()
        outer.addLayout(row8)

        # ── Card Buttons ───────────────────────────────────────────────── #
        btn_row = QHBoxLayout()
        btn_row.setSpacing(5)

        self.save_btn = QPushButton("Save Entry")
        self.save_btn.setFixedWidth(120)
        self.save_btn.setStyleSheet(button_style)
        self.save_btn.clicked.connect(self.save_entry)
        btn_row.addWidget(self.save_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setFixedWidth(120)
        self.edit_btn.setStyleSheet(button_style)
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        btn_row.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete Entry")
        self.delete_btn.setFixedWidth(120)
        self.delete_btn.setStyleSheet(button_style)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_entry)
        btn_row.addWidget(self.delete_btn)

        btn_row.addStretch()
        outer.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    #  Field helpers                                                       #
    # ------------------------------------------------------------------ #

    def _all_fields(self):
        return [
            self.page_no_input, self.book_no_input, self.reg_no_input,
            self.name_input, self.mother_name_input, self.father_name_input,
            self.mother_age_input, self.father_age_input,
            self.sex_combo, self.place_of_birth_combo, self.mother_nationality_combo,
            self.father_nationality_combo, self.attendant_combo, self.late_reg_combo,
            self.type_of_birth_combo, self.marriage_place_input,
            self.maasin_resident_combo, self.soleyte_resident_combo, self.leyte_resident_combo,
            self.date_of_birth_input, self.date_of_reg_input, self.date_of_marriage_input,
        ]

    def _enable_fields(self):
        for f in self._all_fields():
            f.setEnabled(True)
        # Restore marriage date disable rule
        if self.marriage_place_input.currentText() in MARRIAGE_PLACE_NULL_TRIGGERS:
            self.date_of_marriage_input.setEnabled(False)

    def _disable_fields(self):
        for f in self._all_fields():
            f.setEnabled(False)

    def _set_saved_state(self, saved: bool):
        """Toggle field state and button state based on saved status."""
        if saved:
            self._disable_fields()
            self.save_btn.setEnabled(False)
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            self.setStyleSheet(self.styleSheet().replace(
                "background-color: #FFFFFF;\n                border: 1px solid #D1D0D0;",
                "background-color: #dff9e5;\n                border: 1px solid #a3d9b1;"
            ))
        else:
            self._enable_fields()
            self.save_btn.setEnabled(True)
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.setStyleSheet(self.styleSheet().replace(
                "background-color: #dff9e5;\n                border: 1px solid #a3d9b1;",
                "background-color: #FFFFFF;\n                border: 1px solid #D1D0D0;"
            ))

    def _handle_marriage_place_change(self, value):
        if value in MARRIAGE_PLACE_NULL_TRIGGERS:
            self.date_of_marriage_input.setDate(QDate())
            self.date_of_marriage_input.setEnabled(False)
        else:
            self.date_of_marriage_input.setEnabled(True)
            if not self.date_of_marriage_input.date().isValid() or self.date_of_marriage_input.date() == QDate():
                self.date_of_marriage_input.setDate(QDate.currentDate())

    def _on_edit_clicked(self):
        self._enable_fields()
        self.save_btn.setEnabled(True)
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(True)

    # ------------------------------------------------------------------ #
    #  Public: populate from DB row                                        #
    # ------------------------------------------------------------------ #

    def populate(self, row: dict):
        """Fill card fields from a DB result dict. Sets record_id."""
        self.record_id = row.get("id")

        self.page_no_input.setText(str(row["page_no"]) if row.get("page_no") is not None else "")
        self.book_no_input.setText(str(row["book_no"]) if row.get("book_no") is not None else "")
        self.reg_no_input.setText(row.get("reg_no") or "")
        self.name_input.setText(row.get("name") or "")
        self.mother_name_input.setText(row.get("name_of_mother") or "")
        self.father_name_input.setText(row.get("name_of_father") or "")
        self.mother_age_input.setText(str(row["mother_age"]) if row.get("mother_age") is not None else "")
        self.father_age_input.setText(str(row["father_age"]) if row.get("father_age") is not None else "")

        self.sex_combo.setCurrentText(row.get("sex") or "NO ENTRY")
        self.place_of_birth_combo.setCurrentText(row.get("place_of_birth") or "NO ENTRY")
        self.mother_nationality_combo.setCurrentText(row.get("nationality_mother") or "NO ENTRY")
        self.father_nationality_combo.setCurrentText(row.get("nationality_father") or "NO ENTRY")
        self.attendant_combo.setCurrentText(row.get("attendant") or "NO ENTRY")
        self.type_of_birth_combo.setCurrentText(row.get("type_of_birth") or "NO ENTRY")
        self.marriage_place_input.setCurrentText(row.get("parents_marriage_place") or "NO ENTRY")

        late_reg = row.get("late_registration")
        self.late_reg_combo.setCurrentText("YES" if late_reg is True else "NO ENTRY" if late_reg is None else "NO")

        maasin = row.get("maasin_resident")
        self.maasin_resident_combo.setCurrentText("YES" if maasin is True else "NO ENTRY" if maasin is None else "NO")
        soleyte = row.get("soleyte_resident")
        self.soleyte_resident_combo.setCurrentText("YES" if soleyte is True else "NO ENTRY" if soleyte is None else "NO")
        leyte = row.get("leyte_resident")
        self.leyte_resident_combo.setCurrentText("YES" if leyte is True else "NO ENTRY" if leyte is None else "NO")

        dob = row.get("date_of_birth")
        if dob:
            self.date_of_birth_input.setDate(QDate.fromString(dob.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
            self.has_dob_check.setChecked(True)
        else:
            self.date_of_birth_input.setDate(QDate.currentDate())
            self.has_dob_check.setChecked(False)
            self.date_of_birth_input.setEnabled(False)

        dor = row.get("date_of_reg")
        if dor:
            self.date_of_reg_input.setDate(QDate.fromString(dor.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
            self.has_dor_check.setChecked(True)
        else:
            self.date_of_reg_input.setDate(QDate.currentDate())
            self.has_dor_check.setChecked(False)
            self.date_of_reg_input.setEnabled(False)

        dom = row.get("parents_marriage_date")
        if dom:
            self.date_of_marriage_input.setDate(QDate.fromString(dom.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
            self.has_dom_check.setChecked(True)
        else:
            self.has_dom_check.setChecked(False)
            self.date_of_marriage_input.setEnabled(False)

        self._set_saved_state(True)

    def update_entry_number(self, n: int):
        self.entry_number = n
        self.header_label.setText(f"Entry #{n}")

    # ------------------------------------------------------------------ #
    #  Collect values                                                      #
    # ------------------------------------------------------------------ #

    def _collect_values(self):
        """Return a dict of all field values ready for DB insert/update."""
        marriage_place_text = self.marriage_place_input.currentText()
        parents_marriage_place = None if marriage_place_text == "NO ENTRY" else marriage_place_text

        if marriage_place_text in MARRIAGE_PLACE_NULL_TRIGGERS:
            parents_marriage_date = None
        else:
            parents_marriage_date = (
                self.date_of_marriage_input.date().toString("yyyy-MM-dd")
                if self.has_dom_check.isChecked() else None
            )

        late_reg_text = self.late_reg_combo.currentText().strip()
        late_registration = None if late_reg_text == "NO ENTRY" else late_reg_text.lower() == "yes"

        def bool_combo(combo):
            t = combo.currentText().strip()
            return None if t == "NO ENTRY" else t.lower() == "yes"

        return {
            "file_path": self.get_selected_pdf(),
            "page_no": int(self.page_no_input.text()) if self.page_no_input.text() else None,
            "book_no": int(self.book_no_input.text()) if self.book_no_input.text() else None,
            "reg_no": self.reg_no_input.text() or None,
            "name": self.name_input.text() or None,
            "date_of_birth": self.date_of_birth_input.date().toString("yyyy-MM-dd") if self.has_dob_check.isChecked() else None,
            "sex": None if self.sex_combo.currentText() == "NO ENTRY" else self.sex_combo.currentText(),
            "date_of_reg": self.date_of_reg_input.date().toString("yyyy-MM-dd") if self.has_dor_check.isChecked() else None,
            "place_of_birth": None if self.place_of_birth_combo.currentText() == "NO ENTRY" else self.place_of_birth_combo.currentText(),
            "name_of_mother": self.mother_name_input.text() or None,
            "nationality_mother": None if self.mother_nationality_combo.currentText() == "NO ENTRY" else self.mother_nationality_combo.currentText(),
            "name_of_father": self.father_name_input.text() or None,
            "nationality_father": None if self.father_nationality_combo.currentText() == "NO ENTRY" else self.father_nationality_combo.currentText(),
            "parents_marriage_date": parents_marriage_date,
            "parents_marriage_place": parents_marriage_place,
            "attendant": None if self.attendant_combo.currentText() == "NO ENTRY" else self.attendant_combo.currentText(),
            "type_of_birth": None if self.type_of_birth_combo.currentText() == "NO ENTRY" else self.type_of_birth_combo.currentText(),
            "late_registration": late_registration,
            "maasin_resident": bool_combo(self.maasin_resident_combo),
            "soleyte_resident": bool_combo(self.soleyte_resident_combo),
            "leyte_resident": bool_combo(self.leyte_resident_combo),
            "mother_age": int(self.mother_age_input.text()) if self.mother_age_input.text() else None,
            "father_age": int(self.father_age_input.text()) if self.father_age_input.text() else None,
        }

    # ------------------------------------------------------------------ #
    #  Save                                                                #
    # ------------------------------------------------------------------ #

    def save_entry(self):
        file_path = self.get_selected_pdf()
        if not file_path:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Warning")
            box.setText("Please select a PDF file before saving.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
            return

        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Question)
        confirm.setWindowTitle("Confirm Save")
        confirm.setText(f"Save Entry #{self.entry_number}?")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setStyleSheet(message_box_style)
        if confirm.exec() != QMessageBox.Yes:
            return

        conn = self._create_connection()
        cursor = None
        try:
            v = self._collect_values()
            cursor = conn.cursor()

            if self.record_id is None:
                # INSERT
                cursor.execute("""
                    INSERT INTO birth_index (
                        file_path, name, date_of_birth, sex, page_no, book_no, reg_no,
                        date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                        name_of_father, nationality_father, parents_marriage_date,
                        parents_marriage_place, attendant, type_of_birth, late_registration,
                        maasin_resident, soleyte_resident, leyte_resident, mother_age, father_age
                    ) VALUES (
                        %(file_path)s, %(name)s, %(date_of_birth)s, %(sex)s,
                        %(page_no)s, %(book_no)s, %(reg_no)s, %(date_of_reg)s,
                        %(place_of_birth)s, %(name_of_mother)s, %(nationality_mother)s,
                        %(name_of_father)s, %(nationality_father)s, %(parents_marriage_date)s,
                        %(parents_marriage_place)s, %(attendant)s, %(type_of_birth)s,
                        %(late_registration)s, %(maasin_resident)s, %(soleyte_resident)s,
                        %(leyte_resident)s, %(mother_age)s, %(father_age)s
                    ) RETURNING id
                """, v)
                self.record_id = cursor.fetchone()[0]
            else:
                # UPDATE by id
                cursor.execute("""
                    UPDATE birth_index SET
                        name = %(name)s, date_of_birth = %(date_of_birth)s, sex = %(sex)s,
                        page_no = %(page_no)s, book_no = %(book_no)s, reg_no = %(reg_no)s,
                        date_of_reg = %(date_of_reg)s, place_of_birth = %(place_of_birth)s,
                        name_of_mother = %(name_of_mother)s, nationality_mother = %(nationality_mother)s,
                        name_of_father = %(name_of_father)s, nationality_father = %(nationality_father)s,
                        parents_marriage_date = %(parents_marriage_date)s,
                        parents_marriage_place = %(parents_marriage_place)s,
                        attendant = %(attendant)s, type_of_birth = %(type_of_birth)s,
                        late_registration = %(late_registration)s,
                        maasin_resident = %(maasin_resident)s, soleyte_resident = %(soleyte_resident)s,
                        leyte_resident = %(leyte_resident)s, mother_age = %(mother_age)s,
                        father_age = %(father_age)s
                    WHERE id = %(id)s
                """, {**v, "id": self.record_id})

            AuditLogger.log_action(conn, self.current_user, "TAGS_SAVED", {
                "file": file_path, "record_type": "Birth", "entry": self.entry_number
            })

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Success")
            box.setText(f"Entry #{self.entry_number} saved successfully.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()

            self._set_saved_state(True)

        except Exception as e:
            AuditLogger.log_action(conn, self.current_user, "TAG_SAVE_ERROR", {
                "error": str(e), "file": file_path, "entry": self.entry_number
            })
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to save entry: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            if cursor:
                cursor.close()
            self._close_connection()

    # ------------------------------------------------------------------ #
    #  Delete                                                              #
    # ------------------------------------------------------------------ #

    def delete_entry(self):
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Warning)
        confirm.setWindowTitle("Confirm Delete")
        confirm.setText(f"Delete Entry #{self.entry_number}? This cannot be undone.")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setStyleSheet(message_box_style)
        if confirm.exec() != QMessageBox.Yes:
            return

        # If never saved to DB, just remove the card from UI
        if self.record_id is None:
            self.deleted.emit(self)
            return

        conn = self._create_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM birth_index WHERE id = %s", (self.record_id,))

            AuditLogger.log_action(conn, self.current_user, "TAGS_DELETED", {
                "id": self.record_id, "table": "birth_index", "entry": self.entry_number
            })

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Success")
            box.setText(f"Entry #{self.entry_number} deleted.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()

            self.deleted.emit(self)

        except Exception as e:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to delete entry: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            if cursor:
                cursor.close()
            self._close_connection()
