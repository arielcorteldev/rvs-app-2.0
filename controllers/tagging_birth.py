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
from utilities.birth_entry_card import BirthEntryCard
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

        # Card list state
        self._cards = []  # list of BirthEntryCard instances

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

        # ── Card scroll area ──────────────────────────────────────────── #
        self._cards_scroll = QScrollArea()
        self._cards_scroll.setWidgetResizable(True)
        self._cards_scroll.setFixedWidth(750)
        self._cards_scroll.setMinimumHeight(300)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setAlignment(Qt.AlignTop)
        self._cards_layout.setSpacing(10)
        self._cards_scroll.setWidget(self._cards_container)
        main_layout.addWidget(self._cards_scroll)

        # ── Add Entry button ──────────────────────────────────────────── #
        add_entry_btn = QPushButton("+ Add Entry")
        add_entry_btn.setFixedWidth(130)
        add_entry_btn.setStyleSheet(button_style)
        add_entry_btn.clicked.connect(self._add_blank_card)
        main_layout.addWidget(add_entry_btn)


        # PDF List Preview
        self.pdf_list = QListWidget()
        self.pdf_list.setFixedWidth(750)
        self.pdf_list.setMaximumHeight(340)
        self.pdf_list.setIconSize(QSize(100, 140))
        # self.pdf_list.itemClicked.connect(self.show_preview)
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

        self.pdf_viewer = PDFViewer(default_zoom=1.5)
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
                # self.last_page_no = self.page_no_input.text()
                # self.last_book_no = self.book_no_input.text()
                # self.last_reg_date = self.date_of_reg_input.date().toString("yyyy-MM-dd")
                # self.last_place_of_birth = self.place_of_birth_combo.currentText()
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
        """Load all birth_index rows for file_path and populate one card per row."""
        created_connection = self.connection is None
        conn = self.create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, date_of_birth, sex, page_no, book_no, reg_no,
                    date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                    name_of_father, nationality_father, parents_marriage_date,
                    parents_marriage_place, attendant, type_of_birth, late_registration,
                    maasin_resident, soleyte_resident, leyte_resident, mother_age, father_age
                FROM birth_index
                WHERE file_path = %s
                ORDER BY id ASC
            """, (file_path,))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
        finally:
            if cursor:
                cursor.close()
            if created_connection:
                self.closeConnection()

        # Clear existing cards
        self._clear_cards()

        if rows:
            for row in rows:
                row_dict = dict(zip(columns, row))
                card = self._add_blank_card()
                card.populate(row_dict)
        else:
            # New file — add one blank card ready to fill in
            self._add_blank_card()

    # ------------------------------------------------------------------ #
    #  Card management                                                     #
    # ------------------------------------------------------------------ #

    def _add_blank_card(self):
        """Append a new blank BirthEntryCard and return it."""
        card = BirthEntryCard(
            entry_number=len(self._cards) + 1,
            current_user=self.current_user,
            get_selected_pdf_fn=self.get_selected_pdf,
        )
        card.deleted.connect(self._on_card_deleted)
        self._cards.append(card)
        self._cards_layout.addWidget(card)
        # Scroll to the new card
        QApplication.processEvents()
        self._cards_scroll.verticalScrollBar().setValue(
            self._cards_scroll.verticalScrollBar().maximum()
        )
        return card

    def _clear_cards(self):
        """Remove all cards from the layout and list."""
        for card in self._cards:
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

    def _on_card_deleted(self, card):
        """Called when a card emits deleted signal — remove from UI and reindex."""
        self._cards_layout.removeWidget(card)
        card.deleteLater()
        self._cards.remove(card)
        # Reindex remaining cards
        for i, c in enumerate(self._cards, 1):
            c.update_entry_number(i)
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






