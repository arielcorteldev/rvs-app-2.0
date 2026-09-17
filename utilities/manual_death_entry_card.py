"""ManualDeathEntryCard — a self-contained card widget for tagging a Death
record that has not been scanned yet.

Companion to utilities/death_entry_card.py's DeathEntryCard, but with no
get_selected_pdf_fn dependency (file_path is always saved as NULL) and
scanned explicitly set to False on insert. Used by controllers'
ManualDeathEntryWindow. DeathEntryCard itself is unchanged.

Mirrors utilities/manual_birth_entry_card.py's structure and conventions
(_apply_default_values / reset / load_from_record), adapted to Death's
field set.
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QCheckBox, QPushButton, QMessageBox
)
from PySide6.QtCore import QDate

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


class ManualDeathEntryCard(QFrame):
    """A self-contained card widget for one manually-tagged (unscanned) death record."""

    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
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
            QComboBox { font-weight: bold; }
            QDateEdit { font-weight: bold; }
        """)

        self._build_ui()
        self._apply_default_values()

        # Duplicate-check state — see _check_for_existing_record()
        self._last_duplicate_check = None
        self.reg_no_input.editingFinished.connect(self._check_for_existing_record)
        self.name_input.editingFinished.connect(self._check_for_existing_record)

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
        self.header_label = QLabel("Death Record — Manual Entry")
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
    #  Reset — used when the window is closed/reopened (cached instance)   #
    # ------------------------------------------------------------------ #

    def reset(self):
        """Clear the card back to a blank, editable state. Does not touch the DB."""
        self.record_id = None
        self._last_duplicate_check = None
        self._apply_default_values()
        self._set_saved_state(False)

    def _apply_default_values(self):
        """Set every field to the same state a freshly built card starts in.

        Combos default to whatever addItems() put first (index 0) — this is
        the single place that defines "blank card," used by both __init__
        and reset().
        """
        self.page_no_input.clear()
        self.book_no_input.clear()
        self.reg_no_input.clear()
        self.name_input.clear()
        self.age_input.clear()
        self.age_months_input.clear()
        self.age_days_input.clear()
        self.age_hours_input.clear()
        self.age_mins_input.clear()
        self.cause_of_death_input.clear()
        self.residence_input.clear()

        self.sex_combo.setCurrentIndex(0)
        self.civil_status_combo.setCurrentIndex(0)
        self.nationality_combo.setCurrentIndex(0)
        self.death_place_input.setCurrentIndex(0)
        self.corpse_disposal_combo.setCurrentIndex(0)
        self.attendant_combo.setCurrentIndex(0)
        self.late_reg_combo.setCurrentIndex(0)
        self.maasin_resident_combo.setCurrentIndex(0)
        self.soleyte_resident_combo.setCurrentIndex(0)
        self.leyte_resident_combo.setCurrentIndex(0)

        self.date_of_death_input.setDate(QDate.currentDate())
        self.has_dod_check.setChecked(True)
        self.date_of_birth_input.setDate(QDate.currentDate())
        self.has_dob_check.setChecked(True)
        self.date_of_reg_input.setDate(QDate.currentDate())
        self.has_dor_check.setChecked(True)

    # ------------------------------------------------------------------ #
    #  Load an existing record — used when reopening a saved manual entry  #
    #  for editing (e.g. via Verify's "not yet scanned" prompt), rather    #
    #  than starting a fresh blank entry.                                  #
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Duplicate check — before a NEW manual entry is created, see if a    #
    #  matching record (scanned or another manual entry) already exists.  #
    # ------------------------------------------------------------------ #

    def _check_for_existing_record(self):
        """If this is still a blank/new card and both Reg. No. and Name are
        filled in, check whether a matching death_index row already exists.

        - If it's already scanned/tagged: block — that record is already
          searchable and auto-populatable via Verify, no reason to create
          a duplicate manual entry for it.
        - If it's another manual (unscanned) entry: open that one instead
          of creating a second one for the same person.
        """
        if self.record_id is not None:
            return

        reg_no = self.reg_no_input.text().strip()
        name = self.name_input.text().strip()
        if not reg_no or not name:
            return

        check_key = (reg_no, name)
        if check_key == self._last_duplicate_check:
            return
        self._last_duplicate_check = check_key

        conn = self._create_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, scanned
                FROM death_index
                WHERE reg_no = %s AND name ILIKE %s
                LIMIT 1
            """, (reg_no, name))
            row = cursor.fetchone()
        finally:
            if cursor:
                cursor.close()
            self._close_connection()

        if not row:
            return

        existing_id, existing_scanned = row

        if existing_scanned:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Record Already Exists")
            box.setText(
                f"A record for Reg. No. {reg_no} — {name} has already been scanned and "
                "tagged. It's already searchable and can generate an LCR certificate "
                "through Verify — there's no need to create a manual entry for it. "
                "This window will now close."
            )
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
            self.window().close()
            return

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("Manual Entry Already Exists")
        box.setText(
            f"A manual entry already exists for Reg. No. {reg_no} — {name}. "
            "Opening that record for editing."
        )
        box.setStandardButtons(QMessageBox.Ok)
        box.setStyleSheet(message_box_style)
        box.exec()

        self.load_from_record(existing_id)

    def load_from_record(self, record_id):
        """Populate the card from an existing death_index row and put it
        into the saved/editable state (Edit + Delete available, fields
        disabled until Edit is clicked). Returns True on success."""
        conn = self._create_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT page_no, book_no, reg_no, name, date_of_death, date_of_birth, sex,
                       date_of_reg, age_years, age_months, age_days, age_hours, age_mins,
                       civil_status, nationality, place_of_death, cause_of_death,
                       corpse_disposal, late_registration, maasin_resident, soleyte_resident,
                       leyte_resident, attendant, residence
                FROM death_index WHERE id = %s
            """, (record_id,))
            row = cursor.fetchone()
            if not row:
                return False

            (page_no, book_no, reg_no, name, date_of_death, date_of_birth, sex,
             date_of_reg, age_years, age_months, age_days, age_hours, age_mins,
             civil_status, nationality, place_of_death, cause_of_death,
             corpse_disposal, late_registration, maasin_resident, soleyte_resident,
             leyte_resident, attendant, residence) = row

            self.record_id = record_id

            self.page_no_input.setText(str(page_no) if page_no is not None else "")
            self.book_no_input.setText(str(book_no) if book_no is not None else "")
            self.reg_no_input.setText(reg_no or "")
            self.name_input.setText(name or "")
            self.age_input.setText(str(age_years) if age_years is not None else "")
            self.age_months_input.setText(str(age_months) if age_months is not None else "")
            self.age_days_input.setText(str(age_days) if age_days is not None else "")
            self.age_hours_input.setText(str(age_hours) if age_hours is not None else "")
            self.age_mins_input.setText(str(age_mins) if age_mins is not None else "")
            self.cause_of_death_input.setText(cause_of_death or "")
            self.residence_input.setText(residence or "")

            self.sex_combo.setCurrentText(sex or "NO ENTRY")
            self.civil_status_combo.setCurrentText(civil_status or "NO ENTRY")
            self.nationality_combo.setCurrentText(nationality or "NO ENTRY")
            self.death_place_input.setCurrentText(place_of_death or "NO ENTRY")
            self.corpse_disposal_combo.setCurrentText(corpse_disposal or "NO ENTRY")
            self.attendant_combo.setCurrentText(attendant or "NO ENTRY")

            def bool_to_combo_text(v):
                if v is None:
                    return "NO ENTRY"
                return "YES" if v else "NO"

            self.late_reg_combo.setCurrentText(bool_to_combo_text(late_registration))
            self.maasin_resident_combo.setCurrentText(bool_to_combo_text(maasin_resident))
            self.soleyte_resident_combo.setCurrentText(bool_to_combo_text(soleyte_resident))
            self.leyte_resident_combo.setCurrentText(bool_to_combo_text(leyte_resident))

            def apply_date(value, date_edit, has_check):
                if value:
                    has_check.setChecked(True)
                    date_edit.setDate(QDate(value.year, value.month, value.day))
                else:
                    has_check.setChecked(False)
                    date_edit.setDate(QDate.currentDate())

            apply_date(date_of_death, self.date_of_death_input, self.has_dod_check)
            apply_date(date_of_birth, self.date_of_birth_input, self.has_dob_check)
            apply_date(date_of_reg, self.date_of_reg_input, self.has_dor_check)

            self._set_saved_state(True)
            return True

        finally:
            if cursor:
                cursor.close()
            self._close_connection()

    # ------------------------------------------------------------------ #
    #  Collect values                                                      #
    # ------------------------------------------------------------------ #

    def _collect_values(self):
        def parse_int(text):
            return int(text) if text and text.strip().isdigit() else None

        def bool_val(combo):
            t = combo.currentText().strip()
            return None if t == "NO ENTRY" else t.lower() == "yes"

        late_reg_text = self.late_reg_combo.currentText().strip()
        late_registration = None if late_reg_text == "NO ENTRY" else late_reg_text.lower() == "yes"

        return {
            "file_path": None,  # manual entries have no scanned file
            "scanned": False,
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
        if not self.reg_no_input.text().strip():
            warn = QMessageBox(self)
            warn.setIcon(QMessageBox.Warning)
            warn.setWindowTitle("Missing Registry No.")
            warn.setText(
                "No Registry No. was entered. Without it, this manual record can't "
                "later be matched to its scanned page once it's scanned and tagged. "
                "Save anyway?"
            )
            warn.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            warn.setStyleSheet(message_box_style)
            if warn.exec() != QMessageBox.Yes:
                return
        else:
            confirm = QMessageBox(self)
            confirm.setIcon(QMessageBox.Question)
            confirm.setWindowTitle("Confirm Save")
            confirm.setText("Save this manual record?")
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
                # INSERT — new manual record, no scan attached
                cursor.execute("""
                    INSERT INTO death_index (
                        file_path, scanned, name, date_of_death, date_of_birth, sex, page_no, book_no, reg_no,
                        date_of_reg, age_years, age_months, age_days, age_hours, age_mins,
                        civil_status, nationality, place_of_death, cause_of_death,
                        corpse_disposal, late_registration, maasin_resident, soleyte_resident,
                        leyte_resident, attendant, residence
                    ) VALUES (
                        %(file_path)s, %(scanned)s, %(name)s, %(date_of_death)s, %(date_of_birth)s, %(sex)s,
                        %(page_no)s, %(book_no)s, %(reg_no)s, %(date_of_reg)s,
                        %(age_years)s, %(age_months)s, %(age_days)s, %(age_hours)s, %(age_mins)s,
                        %(civil_status)s, %(nationality)s, %(place_of_death)s, %(cause_of_death)s,
                        %(corpse_disposal)s, %(late_registration)s, %(maasin_resident)s,
                        %(soleyte_resident)s, %(leyte_resident)s, %(attendant)s, %(residence)s
                    ) RETURNING id
                """, v)
                self.record_id = cursor.fetchone()[0]
            else:
                # UPDATE by id — editing an already-saved manual record.
                # file_path / scanned are intentionally left untouched here;
                # only the tagging-side reconciliation flow (not yet built)
                # is allowed to attach a file and flip scanned to true.
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

            AuditLogger.log_action(conn, self.current_user, "MANUAL_TAGS_SAVED", {
                "record_type": "Death", "id": self.record_id
            })

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Success")
            box.setText("Manual record saved successfully.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()

            self._set_saved_state(True)

        except Exception as e:
            AuditLogger.log_action(conn, self.current_user, "MANUAL_TAG_SAVE_ERROR", {
                "error": str(e), "record_type": "Death"
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
        confirm.setText("Delete this manual record? This cannot be undone.")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setStyleSheet(message_box_style)
        if confirm.exec() != QMessageBox.Yes:
            return

        if self.record_id is None:
            self.reset()
            return

        conn = self._create_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM death_index WHERE id = %s", (self.record_id,))

            AuditLogger.log_action(conn, self.current_user, "MANUAL_TAGS_DELETED", {
                "id": self.record_id, "table": "death_index"
            })

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Success")
            box.setText("Manual record deleted.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()

            self.reset()

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