from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QCheckBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QDate, Signal

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

NATIONALITY_ITEMS = [
    "FILIPINO", "CHINESE", "INDIAN", "AMERICAN", "JAPANESE", "SOUTH KOREAN",
    "GERMAN", "AUSTRALIAN", "TAIWANESE", "INDONESIAN", "VIETNAMESE", "UNKNOWN"
]


class MarriageEntryCard(QFrame):
    """A self-contained card widget representing one marriage record entry."""

    deleted = Signal(object)

    def __init__(self, entry_number, current_user, get_selected_pdf_fn, parent=None):
        super().__init__(parent)
        self.entry_number = entry_number
        self.current_user = current_user
        self.get_selected_pdf = get_selected_pdf_fn
        self.record_id = None
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
            QComboBox { font-weight: bold; }
            QDateEdit { font-weight: bold; }
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

    def _date_col(self, label_text, attr_name, check_attr, width=200):
        col = QVBoxLayout()
        lbl_row = QHBoxLayout(); lbl_row.setSpacing(5)
        lbl_row.addWidget(self._label(label_text))
        chk = QCheckBox("Has Date"); chk.setChecked(True); chk.setStyleSheet(CHECKBOX_STYLE)
        setattr(self, check_attr, chk)
        lbl_row.addWidget(chk); lbl_row.addStretch()
        col.addLayout(lbl_row)
        de = QDateEdit(); de.setCalendarPopup(True); de.setDate(QDate.currentDate())
        de.setFixedWidth(width); de.setStyleSheet(date_picker_style)
        setattr(self, attr_name, de)
        chk.stateChanged.connect(lambda: de.setEnabled(chk.isChecked()))
        col.addWidget(de)
        return col

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────── #
        hdr = QHBoxLayout()
        self.header_label = QLabel(f"Entry #{self.entry_number}")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #ce305e; border: none;")
        hdr.addWidget(self.header_label); hdr.addStretch()
        outer.addLayout(hdr)

        # ── Row 1: Page No, Book No, Reg No ───────────────────────────── #
        row1 = QHBoxLayout(); row1.setSpacing(10)
        for attr, ph in [("page_no_input", "Page No."), ("book_no_input", "Book No."), ("reg_no_input", "Registry No.")]:
            inp = QLineEdit(); inp.setPlaceholderText(ph); inp.setFixedWidth(200)
            setattr(self, attr, inp)
            c = QVBoxLayout(); c.addWidget(self._label(ph + ":")); c.addWidget(inp)
            row1.addLayout(c)
        row1.addStretch()
        outer.addLayout(row1)

        # ── HUSBAND SECTION ───────────────────────────────────────────── #
        husband_lbl = QLabel("── Husband ──")
        husband_lbl.setStyleSheet("font-weight: bold; color: #ce305e; border: none;")
        outer.addWidget(husband_lbl)

        # Husband Name and Age
        row_h1 = QHBoxLayout(); row_h1.setSpacing(10)
        self.husband_name_input = QLineEdit(); self.husband_name_input.setPlaceholderText("Husband Name"); self.husband_name_input.setFixedWidth(500)
        c = QVBoxLayout(); c.addWidget(self._label("Husband Name:")); c.addWidget(self.husband_name_input)
        row_h1.addLayout(c)
        self.husband_age_input = QLineEdit(); self.husband_age_input.setPlaceholderText("Age"); self.husband_age_input.setFixedWidth(100)
        c = QVBoxLayout(); c.addWidget(self._label("Age:")); c.addWidget(self.husband_age_input)
        row_h1.addLayout(c)
        row_h1.addStretch()
        outer.addLayout(row_h1)

        # Husband Nationality and Civil Status
        row_h2 = QHBoxLayout(); row_h2.setSpacing(10)
        self.husband_nationality_combo = QComboBox(); self.husband_nationality_combo.setEditable(True)
        self.husband_nationality_combo.addItems(NATIONALITY_ITEMS); self.husband_nationality_combo.setFixedWidth(350)
        self.husband_nationality_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Nationality:")); c.addWidget(self.husband_nationality_combo)
        row_h2.addLayout(c)
        self.husband_civil_status_combo = QComboBox()
        self.husband_civil_status_combo.addItems(["SINGLE", "WIDOWER", "DIVORCED", "ANNULLED", "UNKNOWN"])
        self.husband_civil_status_combo.setFixedWidth(300); self.husband_civil_status_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Civil Status:")); c.addWidget(self.husband_civil_status_combo)
        row_h2.addLayout(c)
        row_h2.addStretch()
        outer.addLayout(row_h2)

        # Husband Parents
        row_h3 = QHBoxLayout(); row_h3.setSpacing(10)
        self.husband_father_name_input = QLineEdit(); self.husband_father_name_input.setPlaceholderText("Name of Father"); self.husband_father_name_input.setFixedWidth(325)
        c = QVBoxLayout(); c.addWidget(self._label("Name of Father:")); c.addWidget(self.husband_father_name_input)
        row_h3.addLayout(c)
        self.husband_mother_name_input = QLineEdit(); self.husband_mother_name_input.setPlaceholderText("Name of Mother"); self.husband_mother_name_input.setFixedWidth(325)
        c = QVBoxLayout(); c.addWidget(self._label("Name of Mother:")); c.addWidget(self.husband_mother_name_input)
        row_h3.addLayout(c)
        row_h3.addStretch()
        outer.addLayout(row_h3)

        # ── WIFE SECTION ──────────────────────────────────────────────── #
        wife_lbl = QLabel("── Wife ──")
        wife_lbl.setStyleSheet("font-weight: bold; color: #ce305e; border: none;")
        outer.addWidget(wife_lbl)

        # Wife Name and Age
        row_w1 = QHBoxLayout(); row_w1.setSpacing(10)
        self.wife_name_input = QLineEdit(); self.wife_name_input.setPlaceholderText("Wife Name"); self.wife_name_input.setFixedWidth(500)
        c = QVBoxLayout(); c.addWidget(self._label("Wife Name:")); c.addWidget(self.wife_name_input)
        row_w1.addLayout(c)
        self.wife_age_input = QLineEdit(); self.wife_age_input.setPlaceholderText("Age"); self.wife_age_input.setFixedWidth(100)
        c = QVBoxLayout(); c.addWidget(self._label("Age:")); c.addWidget(self.wife_age_input)
        row_w1.addLayout(c)
        row_w1.addStretch()
        outer.addLayout(row_w1)

        # Wife Nationality and Civil Status
        row_w2 = QHBoxLayout(); row_w2.setSpacing(10)
        self.wife_nationality_combo = QComboBox(); self.wife_nationality_combo.setEditable(True)
        self.wife_nationality_combo.addItems(NATIONALITY_ITEMS); self.wife_nationality_combo.setFixedWidth(350)
        self.wife_nationality_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Nationality:")); c.addWidget(self.wife_nationality_combo)
        row_w2.addLayout(c)
        self.wife_civil_status_combo = QComboBox()
        self.wife_civil_status_combo.addItems(["SINGLE", "WIDOW", "DIVORCED", "ANNULLED", "UNKNOWN"])
        self.wife_civil_status_combo.setFixedWidth(300); self.wife_civil_status_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Civil Status:")); c.addWidget(self.wife_civil_status_combo)
        row_w2.addLayout(c)
        row_w2.addStretch()
        outer.addLayout(row_w2)

        # Wife Parents
        row_w3 = QHBoxLayout(); row_w3.setSpacing(10)
        self.wife_father_name_input = QLineEdit(); self.wife_father_name_input.setPlaceholderText("Name of Father"); self.wife_father_name_input.setFixedWidth(325)
        c = QVBoxLayout(); c.addWidget(self._label("Name of Father:")); c.addWidget(self.wife_father_name_input)
        row_w3.addLayout(c)
        self.wife_mother_name_input = QLineEdit(); self.wife_mother_name_input.setPlaceholderText("Name of Mother"); self.wife_mother_name_input.setFixedWidth(325)
        c = QVBoxLayout(); c.addWidget(self._label("Name of Mother:")); c.addWidget(self.wife_mother_name_input)
        row_w3.addLayout(c)
        row_w3.addStretch()
        outer.addLayout(row_w3)

        # ── MARRIAGE INFO ─────────────────────────────────────────────── #
        row_m1 = QHBoxLayout(); row_m1.setSpacing(10)
        row_m1.addLayout(self._date_col("Date of Marriage:", "date_of_marriage_input", "has_dom_check", 220))

        self.place_of_marriage_combo = QComboBox(); self.place_of_marriage_combo.setEditable(True)
        self.place_of_marriage_combo.addItems([
            "NATIONAL SHRINE AND PARISH OF OUR LADY OF THE ASSUMPTION, MAASIN CITY, SO. LEYTE",
            "ASSUMPTION IN THE HILLS PARISH, ASUNCION, MAASIN CITY, SO. LEYTE",
            "STO. NIÑO DE IBARRA PARISH, IBARRA, ASUNCION, MAASIN CITY, SO. LEYTE",
            "MUNICIPAL TRIAL COURT IN CITIES, MAASIN CITY, SO. LEYTE",
            "OFFICE OF THE CITY MAYOR, MAASIN CITY, SO. LEYTE",
            "UNKNOWN"
        ])
        self.place_of_marriage_combo.setFixedWidth(450); self.place_of_marriage_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Place of Marriage:")); c.addWidget(self.place_of_marriage_combo)
        row_m1.addLayout(c)
        row_m1.addStretch()
        outer.addLayout(row_m1)

        # Ceremony Type, Late Reg, Date of Reg
        row_m2 = QHBoxLayout(); row_m2.setSpacing(10)
        self.ceremony_type_combo = QComboBox(); self.ceremony_type_combo.setEditable(True)
        self.ceremony_type_combo.addItems([
            "ROMAN CATHOLIC WEDDING", "CIVIL WEDDING", "OTHER RELIGIOUS WEDDING", "UNKNOWN"
        ])
        self.ceremony_type_combo.setFixedWidth(270); self.ceremony_type_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Ceremony Type:")); c.addWidget(self.ceremony_type_combo)
        row_m2.addLayout(c)

        self.late_reg_combo = QComboBox(); self.late_reg_combo.addItems(["NO", "YES", "NO ENTRY"])
        self.late_reg_combo.setFixedWidth(200); self.late_reg_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Late Registration:")); c.addWidget(self.late_reg_combo)
        row_m2.addLayout(c)

        row_m2.addLayout(self._date_col("Date of Registration:", "date_of_reg_input", "has_dor_check", 200))
        row_m2.addStretch()
        outer.addLayout(row_m2)

        # ── Card Buttons ───────────────────────────────────────────────── #
        btn_row = QHBoxLayout(); btn_row.setSpacing(5)
        self.save_btn = QPushButton("Save Entry"); self.save_btn.setFixedWidth(120); self.save_btn.setStyleSheet(button_style)
        self.save_btn.clicked.connect(self.save_entry)
        btn_row.addWidget(self.save_btn)

        self.edit_btn = QPushButton("Edit"); self.edit_btn.setFixedWidth(120); self.edit_btn.setStyleSheet(button_style)
        self.edit_btn.setEnabled(False); self.edit_btn.clicked.connect(self._on_edit_clicked)
        btn_row.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete Entry"); self.delete_btn.setFixedWidth(120); self.delete_btn.setStyleSheet(button_style)
        self.delete_btn.setEnabled(False); self.delete_btn.clicked.connect(self.delete_entry)
        btn_row.addWidget(self.delete_btn)

        btn_row.addStretch()
        outer.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    #  Field helpers                                                       #
    # ------------------------------------------------------------------ #

    def _all_fields(self):
        return [
            self.page_no_input, self.book_no_input, self.reg_no_input,
            self.husband_name_input, self.husband_age_input,
            self.husband_father_name_input, self.husband_mother_name_input,
            self.wife_name_input, self.wife_age_input,
            self.wife_father_name_input, self.wife_mother_name_input,
            self.husband_nationality_combo, self.husband_civil_status_combo,
            self.wife_nationality_combo, self.wife_civil_status_combo,
            self.place_of_marriage_combo, self.ceremony_type_combo, self.late_reg_combo,
            self.date_of_marriage_input, self.date_of_reg_input,
        ]

    def _enable_fields(self):
        for f in self._all_fields(): f.setEnabled(True)

    def _disable_fields(self):
        for f in self._all_fields(): f.setEnabled(False)

    def _set_saved_state(self, saved: bool):
        if saved:
            self._disable_fields()
            self.save_btn.setEnabled(False); self.edit_btn.setEnabled(True); self.delete_btn.setEnabled(True)
            self.setStyleSheet(self.styleSheet().replace(
                "background-color: #FFFFFF;\n                border: 1px solid #D1D0D0;",
                "background-color: #dff9e5;\n                border: 1px solid #a3d9b1;"
            ))
        else:
            self._enable_fields()
            self.save_btn.setEnabled(True); self.edit_btn.setEnabled(False); self.delete_btn.setEnabled(False)
            self.setStyleSheet(self.styleSheet().replace(
                "background-color: #dff9e5;\n                border: 1px solid #a3d9b1;",
                "background-color: #FFFFFF;\n                border: 1px solid #D1D0D0;"
            ))

    def _on_edit_clicked(self):
        self._enable_fields()
        self.save_btn.setEnabled(True); self.edit_btn.setEnabled(False); self.delete_btn.setEnabled(True)

    # ------------------------------------------------------------------ #
    #  Public: populate from DB row                                        #
    # ------------------------------------------------------------------ #

    def populate(self, row: dict):
        self.record_id = row.get("id")

        self.page_no_input.setText(str(row["page_no"]) if row.get("page_no") is not None else "")
        self.book_no_input.setText(str(row["book_no"]) if row.get("book_no") is not None else "")
        self.reg_no_input.setText(row.get("reg_no") or "")
        self.husband_name_input.setText(row.get("husband_name") or "")
        self.husband_age_input.setText(str(row["husband_age"]) if row.get("husband_age") is not None else "")
        self.husband_father_name_input.setText(row.get("husb_father") or "")
        self.husband_mother_name_input.setText(row.get("husb_mother") or "")
        self.wife_name_input.setText(row.get("wife_name") or "")
        self.wife_age_input.setText(str(row["wife_age"]) if row.get("wife_age") is not None else "")
        self.wife_father_name_input.setText(row.get("wife_father") or "")
        self.wife_mother_name_input.setText(row.get("wife_mother") or "")

        self.husband_nationality_combo.setCurrentText(row.get("husb_nationality") or "UNKNOWN")
        self.husband_civil_status_combo.setCurrentText(row.get("husb_civil_status") or "UNKNOWN")
        self.wife_nationality_combo.setCurrentText(row.get("wife_nationality") or "UNKNOWN")
        self.wife_civil_status_combo.setCurrentText(row.get("wife_civil_status") or "UNKNOWN")
        self.place_of_marriage_combo.setCurrentText(row.get("place_of_marriage") or "UNKNOWN")
        self.ceremony_type_combo.setCurrentText(row.get("ceremony_type") or "UNKNOWN")

        late_reg = row.get("late_registration")
        self.late_reg_combo.setCurrentText("YES" if late_reg is True else "NO ENTRY" if late_reg is None else "NO")

        for date_val, input_attr, check_attr in [
            (row.get("date_of_marriage"), "date_of_marriage_input", "has_dom_check"),
            (row.get("date_of_reg"), "date_of_reg_input", "has_dor_check"),
        ]:
            inp = getattr(self, input_attr)
            chk = getattr(self, check_attr)
            if date_val:
                inp.setDate(QDate.fromString(date_val.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                chk.setChecked(True)
            else:
                inp.setDate(QDate.currentDate()); chk.setChecked(False); inp.setEnabled(False)

        self._set_saved_state(True)

    def update_entry_number(self, n: int):
        self.entry_number = n
        self.header_label.setText(f"Entry #{n}")

    # ------------------------------------------------------------------ #
    #  Collect values                                                      #
    # ------------------------------------------------------------------ #

    def _collect_values(self):
        def parse_int(text):
            return int(text) if text and text.strip().isdigit() else None

        late_reg_text = self.late_reg_combo.currentText().strip()
        late_registration = None if late_reg_text == "NO ENTRY" else late_reg_text.lower() == "yes"

        return {
            "file_path": self.get_selected_pdf(),
            "page_no": parse_int(self.page_no_input.text()),
            "book_no": parse_int(self.book_no_input.text()),
            "reg_no": self.reg_no_input.text() or None,
            "husband_name": self.husband_name_input.text() or None,
            "husband_age": parse_int(self.husband_age_input.text()),
            "husb_nationality": None if self.husband_nationality_combo.currentText() == "UNKNOWN" else self.husband_nationality_combo.currentText(),
            "husb_civil_status": None if self.husband_civil_status_combo.currentText() == "UNKNOWN" else self.husband_civil_status_combo.currentText(),
            "husb_father": self.husband_father_name_input.text() or None,
            "husb_mother": self.husband_mother_name_input.text() or None,
            "wife_name": self.wife_name_input.text() or None,
            "wife_age": parse_int(self.wife_age_input.text()),
            "wife_nationality": None if self.wife_nationality_combo.currentText() == "UNKNOWN" else self.wife_nationality_combo.currentText(),
            "wife_civil_status": None if self.wife_civil_status_combo.currentText() == "UNKNOWN" else self.wife_civil_status_combo.currentText(),
            "wife_father": self.wife_father_name_input.text() or None,
            "wife_mother": self.wife_mother_name_input.text() or None,
            "date_of_marriage": self.date_of_marriage_input.date().toString("yyyy-MM-dd") if self.has_dom_check.isChecked() else None,
            "place_of_marriage": None if self.place_of_marriage_combo.currentText() == "UNKNOWN" else self.place_of_marriage_combo.currentText(),
            "ceremony_type": None if self.ceremony_type_combo.currentText() == "UNKNOWN" else self.ceremony_type_combo.currentText(),
            "late_registration": late_registration,
            "date_of_reg": self.date_of_reg_input.date().toString("yyyy-MM-dd") if self.has_dor_check.isChecked() else None,
        }

    # ------------------------------------------------------------------ #
    #  Save                                                                #
    # ------------------------------------------------------------------ #

    def save_entry(self):
        file_path = self.get_selected_pdf()
        if not file_path:
            box = QMessageBox(self); box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Warning"); box.setText("Please select a PDF file before saving.")
            box.setStandardButtons(QMessageBox.Ok); box.setStyleSheet(message_box_style); box.exec()
            return

        confirm = QMessageBox(self); confirm.setIcon(QMessageBox.Question)
        confirm.setWindowTitle("Confirm Save"); confirm.setText(f"Save Entry #{self.entry_number}?")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No); confirm.setStyleSheet(message_box_style)
        if confirm.exec() != QMessageBox.Yes:
            return

        conn = self._create_connection()
        cursor = None
        try:
            v = self._collect_values()
            cursor = conn.cursor()

            if self.record_id is None:
                cursor.execute("""
                    INSERT INTO marriage_index (
                        file_path, page_no, book_no, reg_no,
                        husband_name, husband_age, husb_nationality, husb_civil_status, husb_father, husb_mother,
                        wife_name, wife_age, wife_nationality, wife_civil_status, wife_father, wife_mother,
                        date_of_marriage, place_of_marriage, ceremony_type, late_registration, date_of_reg
                    ) VALUES (
                        %(file_path)s, %(page_no)s, %(book_no)s, %(reg_no)s,
                        %(husband_name)s, %(husband_age)s, %(husb_nationality)s, %(husb_civil_status)s, %(husb_father)s, %(husb_mother)s,
                        %(wife_name)s, %(wife_age)s, %(wife_nationality)s, %(wife_civil_status)s, %(wife_father)s, %(wife_mother)s,
                        %(date_of_marriage)s, %(place_of_marriage)s, %(ceremony_type)s, %(late_registration)s, %(date_of_reg)s
                    ) RETURNING id
                """, v)
                self.record_id = cursor.fetchone()[0]
            else:
                cursor.execute("""
                    UPDATE marriage_index SET
                        page_no=%(page_no)s, book_no=%(book_no)s, reg_no=%(reg_no)s,
                        husband_name=%(husband_name)s, husband_age=%(husband_age)s,
                        husb_nationality=%(husb_nationality)s, husb_civil_status=%(husb_civil_status)s,
                        husb_father=%(husb_father)s, husb_mother=%(husb_mother)s,
                        wife_name=%(wife_name)s, wife_age=%(wife_age)s,
                        wife_nationality=%(wife_nationality)s, wife_civil_status=%(wife_civil_status)s,
                        wife_father=%(wife_father)s, wife_mother=%(wife_mother)s,
                        date_of_marriage=%(date_of_marriage)s, place_of_marriage=%(place_of_marriage)s,
                        ceremony_type=%(ceremony_type)s, late_registration=%(late_registration)s,
                        date_of_reg=%(date_of_reg)s
                    WHERE id=%(id)s
                """, {**v, "id": self.record_id})

            AuditLogger.log_action(conn, self.current_user, "TAGS_SAVED", {
                "file": file_path, "record_type": "Marriage", "entry": self.entry_number
            })

            box = QMessageBox(self); box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Success"); box.setText(f"Entry #{self.entry_number} saved successfully.")
            box.setStandardButtons(QMessageBox.Ok); box.setStyleSheet(message_box_style); box.exec()
            self._set_saved_state(True)

        except Exception as e:
            box = QMessageBox(self); box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error"); box.setText(f"Failed to save entry: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok); box.setStyleSheet(message_box_style); box.exec()
        finally:
            if cursor: cursor.close()
            self._close_connection()

    # ------------------------------------------------------------------ #
    #  Delete                                                              #
    # ------------------------------------------------------------------ #

    def delete_entry(self):
        confirm = QMessageBox(self); confirm.setIcon(QMessageBox.Warning)
        confirm.setWindowTitle("Confirm Delete")
        confirm.setText(f"Delete Entry #{self.entry_number}? This cannot be undone.")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No); confirm.setStyleSheet(message_box_style)
        if confirm.exec() != QMessageBox.Yes:
            return

        if self.record_id is None:
            self.deleted.emit(self)
            return

        conn = self._create_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM marriage_index WHERE id = %s", (self.record_id,))
            AuditLogger.log_action(conn, self.current_user, "TAGS_DELETED", {
                "id": self.record_id, "table": "marriage_index", "entry": self.entry_number
            })
            box = QMessageBox(self); box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Success"); box.setText(f"Entry #{self.entry_number} deleted.")
            box.setStandardButtons(QMessageBox.Ok); box.setStyleSheet(message_box_style); box.exec()
            self.deleted.emit(self)
        except Exception as e:
            box = QMessageBox(self); box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error"); box.setText(f"Failed to delete entry: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok); box.setStyleSheet(message_box_style); box.exec()
        finally:
            if cursor: cursor.close()
            self._close_connection()
