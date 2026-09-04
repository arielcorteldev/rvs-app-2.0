"""ManualBirthEntryWindow — standalone window for tagging a Live Birth
record that has not been scanned yet.

Opened from verify.py's create_form button (Birth window) in place of the
old blank-PDF-form workflow. Cached/reused via app.py's self.windows
pattern, same as every other window in the app. Uses ManualBirthEntryCard
(utilities/manual_birth_entry_card.py) for the actual fields — this file
just hosts it in a window and owns the reminder pop-up / close behavior.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from utilities.stylesheets import message_box_style
from utilities.manual_birth_entry_card import ManualBirthEntryCard


class ManualBirthEntryWindow(QWidget):
    """Standalone window hosting a single ManualBirthEntryCard.

    Opened from verify.py's create_form button (Birth window) in place of
    the old blank-PDF-form workflow. Cached/reused via app.py's self.windows
    pattern, same as every other window in the app.
    """

    def __init__(self, username, parent=None, main_window=None):
        super().__init__(parent)
        self.current_user = username
        self.main_window = main_window

        self.setWindowTitle("Manual Entry — Live Birth")
        self.setWindowIcon(QIcon("assets/icons/application.png"))
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.resize(900, 700)

        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)

        info_label = QLabel(
            "Use this form to tag a Live Birth record that has not been scanned yet. "
            "The saved data can still be used to generate an auto-populated LCR certificate."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #5F5E5A; font-size: 12px; padding: 4px 2px;")
        outer.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.card = ManualBirthEntryCard(current_user=self.current_user)

        scroll.setWidget(self.card)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------ #
    #  Reminder pop-up — shown every time the window is opened             #
    # ------------------------------------------------------------------ #

    def showEvent(self, event):
        super().showEvent(event)
        self._show_reminder()

    def _show_reminder(self):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("Before You Continue")
        box.setText(
            "Make sure you've searched Verify and checked the Digitization Status "
            "Tracker — this record may already exist."
        )
        verify_btn = box.addButton("Open Verify", QMessageBox.ActionRole)
        tracker_btn = box.addButton("Open Digitization Status Tracker", QMessageBox.ActionRole)
        continue_btn = box.addButton("Continue to Manual Entry", QMessageBox.AcceptRole)
        box.setDefaultButton(continue_btn)
        box.setStyleSheet(message_box_style)
        box.exec()

        clicked = box.clickedButton()
        if clicked == verify_btn:
            if self.main_window:
                self.main_window.open_search_birth_dialog()
        elif clicked == tracker_btn:
            if self.main_window:
                self.main_window.open_digitization_status()
        # continue_btn (or dialog dismissed another way): just proceed —
        # this window is already visible underneath.

    # ------------------------------------------------------------------ #
    #  Close — clear, then hide (matches the app's cached-window pattern)  #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        self.card.reset()
        event.ignore()
        self.hide()
