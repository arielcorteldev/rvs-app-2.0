from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QCheckBox, QPushButton, QMessageBox, QApplication
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


class DeathEntryCard(QFrame):
    """A self-contained card widget representing one death record entry."""

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

    def _date_col(self, label_text, attr_name, check_attr):
        """Build a label+checkbox+QDateEdit column and attach to self."""
        col = QVBoxLayout()
        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(5)
        lbl_row.addWidget(self._label(label_text))
        chk = QCheckBox("Has Date")
        chk.setChecked(True)
        chk.setStyleSheet(CHECKBOX_STYLE)
        setattr(self, check_attr, chk)
        lbl_row.addWidget(chk)
        lbl_row.addStretch()
        col.addLayout(lbl_row)

        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setDate(QDate.currentDate())
        de.setFixedWidth(150)
        de.setStyleSheet(date_picker_style)
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
        hdr.addWidget(self.header_label)
        hdr.addStretch()
        outer.addLayout(hdr)

        # ── Row 1: Page No, Book No, Reg No ───────────────────────────── #
        row1 = QHBoxLayout(); row1.setSpacing(10)
        for attr, ph, w in [("page_no_input", "Page No.", 200), ("book_no_input", "Book No.", 200), ("reg_no_input", "Registry No.", 200)]:
            inp = QLineEdit(); inp.setPlaceholderText(ph); inp.setFixedWidth(w)
            setattr(self, attr, inp)
            c = QVBoxLayout(); c.addWidget(self._label(ph + ":")); c.addWidget(inp)
            row1.addLayout(c)
        row1.addStretch()
        outer.addLayout(row1)

        # ── Row 2: Name, Sex ──────────────────────────────────────────── #
        row2 = QHBoxLayout(); row2.setSpacing(10)
        self.name_input = QLineEdit(); self.name_input.setPlaceholderText("Name"); self.name_input.setFixedWidth(400)
        c = QVBoxLayout(); c.addWidget(self._label("Name:")); c.addWidget(self.name_input)
        row2.addLayout(c)

        self.sex_combo = QComboBox(); self.sex_combo.addItems(["MALE", "FEMALE", "NO ENTRY"])
        self.sex_combo.setFixedWidth(200); self.sex_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Sex:")); c.addWidget(self.sex_combo)
        row2.addLayout(c)
        row2.addStretch()
        outer.addLayout(row2)

        # ── Row 3: Date of Death, Date of Birth, Age breakdown ────────── #
        row3 = QHBoxLayout(); row3.setSpacing(10)
        row3.addLayout(self._date_col("Date of Death:", "date_of_death_input", "has_dod_check"))
        row3.addLayout(self._date_col("Date of Birth:", "date_of_birth_input", "has_dob_check"))

        for attr, ph, w in [
            ("age_input", "Age (Years)", 70), ("age_months_input", "Months", 70),
            ("age_days_input", "Days", 70), ("age_hours_input", "Hours", 70), ("age_mins_input", "Minutes", 70)
        ]:
            inp = QLineEdit(); inp.setPlaceholderText(ph); inp.setFixedWidth(w)
            setattr(self, attr, inp)
            lbl = ph.split(" ")[0] + ":"
            c = QVBoxLayout(); c.addWidget(self._label(lbl)); c.addWidget(inp)
            row3.addLayout(c)

        row3.addStretch()
        outer.addLayout(row3)

        # ── Row 4: Place of Death ─────────────────────────────────────── #
        self.death_place_input = QComboBox()
        self.death_place_input.setEditable(True)
        self.death_place_input.addItems([
            "SALVACION OPPUS YÑIGUEZ MEMORIAL PROVINCIAL HOSPITAL",
            "MAASIN MEDCITY HOSPITAL",
            "LIVINGHOPE HOSPITAL, INC.",
            "CM MATERNITY CLINIC",
            "NO ENTRY"
        ])
        self.death_place_input.setFixedWidth(700)
        self.death_place_input.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Place of Death:")); c.addWidget(self.death_place_input)
        outer.addLayout(c)

        # ── Row 5: Civil Status, Nationality, Residence ───────────────── #
        row5 = QHBoxLayout(); row5.setSpacing(10)
        self.civil_status_combo = QComboBox()
        self.civil_status_combo.addItems(["SINGLE", "MARRIED", "WIDOW", "WIDOWER", "DIVORCED", "ANNULLED", "NO ENTRY"])
        self.civil_status_combo.setFixedWidth(120); self.civil_status_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Civil Status:")); c.addWidget(self.civil_status_combo)
        row5.addLayout(c)

        self.nationality_combo = QComboBox(); self.nationality_combo.setEditable(True)
        self.nationality_combo.addItems([
            "FILIPINO", "CHINESE", "INDIAN", "AMERICAN", "JAPANESE", "SOUTH KOREAN",
            "GERMAN", "AUSTRALIAN", "TAIWANESE", "INDONESIAN", "VIETNAMESE", "NO ENTRY"
        ])
        self.nationality_combo.setFixedWidth(160); self.nationality_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Nationality:")); c.addWidget(self.nationality_combo)
        row5.addLayout(c)

        self.residence_input = QLineEdit(); self.residence_input.setPlaceholderText("Residence"); self.residence_input.setFixedWidth(350)
        c = QVBoxLayout(); c.addWidget(self._label("Residence:")); c.addWidget(self.residence_input)
        row5.addLayout(c)
        row5.addStretch()
        outer.addLayout(row5)

        # ── Row 6: Resident combos ─────────────────────────────────────── #
        row6 = QHBoxLayout(); row6.setSpacing(10)
        for attr, lbl in [("maasin_resident_combo", "Maasin Resident:"), ("soleyte_resident_combo", "Soleyte Resident:"), ("leyte_resident_combo", "Leyte Resident:")]:
            cb = QComboBox(); cb.addItems(["NO", "YES", "NO ENTRY"]); cb.setFixedWidth(150); cb.setStyleSheet(combo_box_style)
            setattr(self, attr, cb)
            c = QVBoxLayout(); c.addWidget(self._label(lbl)); c.addWidget(cb)
            row6.addLayout(c)
        row6.addStretch()
        outer.addLayout(row6)

        # ── Row 7: Cause of Death ─────────────────────────────────────── #
        self.cause_of_death_input = QLineEdit(); self.cause_of_death_input.setPlaceholderText("Cause of Death"); self.cause_of_death_input.setFixedWidth(700)
        c = QVBoxLayout(); c.addWidget(self._label("Cause of Death:")); c.addWidget(self.cause_of_death_input)
        outer.addLayout(c)

        # ── Row 8: Corpse Disposal, Attendant, Late Reg, Date of Reg ──── #
        row8 = QHBoxLayout(); row8.setSpacing(10)
        self.corpse_disposal_combo = QComboBox(); self.corpse_disposal_combo.setEditable(True)
        self.corpse_disposal_combo.addItems(["BURIAL", "CREMATION", "OTHERS", "NO ENTRY"])
        self.corpse_disposal_combo.setFixedWidth(130); self.corpse_disposal_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Corpse Disposal:")); c.addWidget(self.corpse_disposal_combo)
        row8.addLayout(c)

        self.attendant_combo = QComboBox(); self.attendant_combo.setEditable(True)
        self.attendant_combo.addItems(["PHYSICIAN", "MIDWIFE", "NURSE", "HILOT", "OTHERS", "NOT APPLICABLE", "NO ENTRY"])
        self.attendant_combo.setFixedWidth(150); self.attendant_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Attendant:")); c.addWidget(self.attendant_combo)
        row8.addLayout(c)

        self.late_reg_combo = QComboBox()
        self.late_reg_combo.addItems(["NO", "YES", "NO ENTRY"])
        self.late_reg_combo.setFixedWidth(130); self.late_reg_combo.setStyleSheet(combo_box_style)
        c = QVBoxLayout(); c.addWidget(self._label("Late Registration:")); c.addWidget(self.late_reg_combo)
        row8.addLayout(c)

        row8.addLayout(self._date_col("Date of Registration:", "date_of_reg_input", "has_dor_check"))
        row8.addStretch()
        outer.addLayout(row8)

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
            self.name_input, self.age_input, self.age_months_input,
            self.age_days_input, self.age_hours_input, self.age_mins_input,
            self.cause_of_death_input, self.residence_input,
            self.sex_combo, self.civil_status_combo, self.nationality_combo,
            self.death_place_input, self.corpse_disposal_combo, self.attendant_combo,
            self.late_reg_combo, self.maasin_resident_combo, self.soleyte_resident_combo,
            self.leyte_resident_combo, self.date_of_death_input, self.date_of_birth_input,
            self.date_of_reg_input,
        ]

    def _enable_fields(self):
        for f in self._all_fields():
            f.setEnabled(True)

    def _disable_fields(self):
        for f in self._all_fields():
            f.setEnabled(False)

    def _set_saved_state(self, saved: bool):
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

    def _on_edit_clicked(self):
        self._enable_fields()
        self.save_btn.setEnabled(True)
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(True)

    # ------------------------------------------------------------------ #
    #  Public: populate from DB row                                        #
    # ------------------------------------------------------------------ #

    def populate(self, row: dict):
        self.record_id = row.get("id")

        self.page_no_input.setText(str(row["page_no"]) if row.get("page_no") is not None else "")
        self.book_no_input.setText(str(row["book_no"]) if row.get("book_no") is not None else "")
        self.reg_no_input.setText(row.get("reg_no") or "")
        self.name_input.setText(row.get("name") or "")
        self.age_input.setText(str(row["age_years"]) if row.get("age_years") is not None else "")
        self.age_months_input.setText(str(row["age_months"]) if row.get("age_months") is not None else "")
        self.age_days_input.setText(str(row["age_days"]) if row.get("age_days") is not None else "")
        self.age_hours_input.setText(str(row["age_hours"]) if row.get("age_hours") is not None else "")
        self.age_mins_input.setText(str(row["age_mins"]) if row.get("age_mins") is not None else "")
        self.cause_of_death_input.setText(row.get("cause_of_death") or "")
        self.residence_input.setText(row.get("residence") or "")

        self.sex_combo.setCurrentText(row.get("sex") or "NO ENTRY")
        self.civil_status_combo.setCurrentText(row.get("civil_status") or "NO ENTRY")
        self.nationality_combo.setCurrentText(row.get("nationality") or "NO ENTRY")
        self.death_place_input.setCurrentText(row.get("place_of_death") or "NO ENTRY")
        self.corpse_disposal_combo.setCurrentText(row.get("corpse_disposal") or "NO ENTRY")
        self.attendant_combo.setCurrentText(row.get("attendant") or "NO ENTRY")

        late_reg = row.get("late_registration")
        self.late_reg_combo.setCurrentText("YES" if late_reg is True else "NO ENTRY" if late_reg is None else "NO")

        def bool_combo(combo, val):
            combo.setCurrentText("YES" if val is True else "NO ENTRY" if val is None else "NO")

        bool_combo(self.maasin_resident_combo, row.get("maasin_resident"))
        bool_combo(self.soleyte_resident_combo, row.get("soleyte_resident"))
        bool_combo(self.leyte_resident_combo, row.get("leyte_resident"))

        for date_val, input_attr, check_attr in [
            (row.get("date_of_death"), "date_of_death_input", "has_dod_check"),
            (row.get("date_of_birth"), "date_of_birth_input", "has_dob_check"),
            (row.get("date_of_reg"), "date_of_reg_input", "has_dor_check"),
        ]:
            inp = getattr(self, input_attr)
            chk = getattr(self, check_attr)
            if date_val:
                inp.setDate(QDate.fromString(date_val.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                chk.setChecked(True)
            else:
                inp.setDate(QDate.currentDate())
                chk.setChecked(False)
                inp.setEnabled(False)

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

        def bool_val(combo):
            t = combo.currentText().strip()
            return None if t in ("NO ENTRY", "UNKNOWN") else t.lower() == "yes"

        late_reg_text = self.late_reg_combo.currentText().strip()
        late_registration = None if late_reg_text == "NO ENTRY" else late_reg_text.lower() == "yes"

        return {
            "file_path": self.get_selected_pdf(),
            "name": self.name_input.text() or None,
            "date_of_death": self.date_of_death_input.date().toString("yyyy-MM-dd") if self.has_dod_check.isChecked() else None,
            "date_of_birth": self.date_of_birth_input.date().toString("yyyy-MM-dd") if self.has_dob_check.isChecked() else None,
            "sex": None if self.sex_combo.currentText() == "NO ENTRY" else self.sex_combo.currentText(),
            "page_no": parse_int(self.page_no_input.text()),
            "book_no": parse_int(self.book_no_input.text()),
            "reg_no": self.reg_no_input.text() or None,
            "date_of_reg": self.date_of_reg_input.date().toString("yyyy-MM-dd") if self.has_dor_check.isChecked() else None,
            "age_years": parse_int(self.age_input.text()),
            "age_months": parse_int(self.age_months_input.text()),
            "age_days": parse_int(self.age_days_input.text()),
            "age_hours": parse_int(self.age_hours_input.text()),
            "age_mins": parse_int(self.age_mins_input.text()),
            "civil_status": None if self.civil_status_combo.currentText() == "NO ENTRY" else self.civil_status_combo.currentText(),
            "nationality": None if self.nationality_combo.currentText() == "NO ENTRY" else self.nationality_combo.currentText(),
            "place_of_death": None if self.death_place_input.currentText() == "NO ENTRY" else self.death_place_input.currentText(),
            "cause_of_death": self.cause_of_death_input.text() or None,
            "corpse_disposal": None if self.corpse_disposal_combo.currentText() == "NO ENTRY" else self.corpse_disposal_combo.currentText(),
            "late_registration": late_registration,
            "maasin_resident": bool_val(self.maasin_resident_combo),
            "soleyte_resident": bool_val(self.soleyte_resident_combo),
            "leyte_resident": bool_val(self.leyte_resident_combo),
            "attendant": None if self.attendant_combo.currentText() == "NO ENTRY" else self.attendant_combo.currentText(),
            "residence": self.residence_input.text() or None,
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
                    INSERT INTO death_index (
                        file_path, name, date_of_death, date_of_birth, sex, page_no, book_no, reg_no,
                        date_of_reg, age_years, age_months, age_days, age_hours, age_mins,
                        civil_status, nationality, place_of_death, cause_of_death,
                        corpse_disposal, late_registration, maasin_resident, soleyte_resident,
                        leyte_resident, attendant, residence
                    ) VALUES (
                        %(file_path)s, %(name)s, %(date_of_death)s, %(date_of_birth)s, %(sex)s,
                        %(page_no)s, %(book_no)s, %(reg_no)s, %(date_of_reg)s,
                        %(age_years)s, %(age_months)s, %(age_days)s, %(age_hours)s, %(age_mins)s,
                        %(civil_status)s, %(nationality)s, %(place_of_death)s, %(cause_of_death)s,
                        %(corpse_disposal)s, %(late_registration)s, %(maasin_resident)s,
                        %(soleyte_resident)s, %(leyte_resident)s, %(attendant)s, %(residence)s
                    ) RETURNING id
                """, v)
                self.record_id = cursor.fetchone()[0]
            else:
                cursor.execute("""
                    UPDATE death_index SET
                        name=%(name)s, date_of_death=%(date_of_death)s, date_of_birth=%(date_of_birth)s,
                        sex=%(sex)s, page_no=%(page_no)s, book_no=%(book_no)s, reg_no=%(reg_no)s,
                        date_of_reg=%(date_of_reg)s, age_years=%(age_years)s, age_months=%(age_months)s,
                        age_days=%(age_days)s, age_hours=%(age_hours)s, age_mins=%(age_mins)s,
                        civil_status=%(civil_status)s, nationality=%(nationality)s,
                        place_of_death=%(place_of_death)s, cause_of_death=%(cause_of_death)s,
                        corpse_disposal=%(corpse_disposal)s, late_registration=%(late_registration)s,
                        maasin_resident=%(maasin_resident)s, soleyte_resident=%(soleyte_resident)s,
                        leyte_resident=%(leyte_resident)s, attendant=%(attendant)s, residence=%(residence)s
                    WHERE id=%(id)s
                """, {**v, "id": self.record_id})

            AuditLogger.log_action(conn, self.current_user, "TAGS_SAVED", {
                "file": file_path, "record_type": "Death", "entry": self.entry_number
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
            if cursor:
                cursor.close()
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
            cursor.execute("DELETE FROM death_index WHERE id = %s", (self.record_id,))
            AuditLogger.log_action(conn, self.current_user, "TAGS_DELETED", {
                "id": self.record_id, "table": "death_index", "entry": self.entry_number
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
            if cursor:
                cursor.close()
            self._close_connection()
