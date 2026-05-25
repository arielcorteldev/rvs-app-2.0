import os
import pymupdf  
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QDate, QSize, QTimer
from PySide6.QtGui import QPixmap, QImage, QIcon
from utilities.stylesheets import button_style

class PDFViewer(QScrollArea):
    """PDF Viewer with zoom support optimized for landscape files."""
    def __init__(self, parent=None, default_zoom=None):
        super().__init__(parent)      
        self.setWidgetResizable(True)
        self.pdf_widget = QWidget()
        # Default layout is horizontal (page 1 left of page 2, etc.)
        self.scroll_mode = "horizontal"  # 'vertical' | 'horizontal'
        self.pdf_layout = QHBoxLayout(self.pdf_widget)
        self.setWidget(self.pdf_widget)

        self.pdf_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
        """)

        self.zoom_factor = 1.0
        self.current_file = None
        self.default_zoom = default_zoom  # Optional default zoom factor (None = auto-zoom)
        self.target_width = 1000  # Target width for landscape pages
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.delayed_resize_render)
        self.last_width = self.width()
        self.manual_zoom = False  # Flag to track if zoom was set manually

        # Apply scrollbar + layout behavior for the default scroll mode.
        self._apply_scroll_mode(rebuild_layout=False)

        # Make adjacent pages look "joined" (no gaps/margins between labels).
        self.pdf_layout.setContentsMargins(0, 0, 0, 0)
        self.pdf_layout.setSpacing(0)

    def set_scroll_mode(self, mode: str):
        """Set page layout direction for scrolling."""
        if not mode:
            mode = "vertical"
        mode = mode.lower().strip()
        if mode not in ("vertical", "horizontal"):
            return
        if mode == self.scroll_mode:
            return

        self.scroll_mode = mode
        self._apply_scroll_mode(rebuild_layout=True)

        # Re-render the current PDF so the layout direction takes effect.
        if self.current_file:
            self.render_pdf()

    def _apply_scroll_mode(self, rebuild_layout: bool):
        """Configure scrollbar policies and optionally rebuild the page layout."""
        if self.scroll_mode == "horizontal":
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        if not rebuild_layout:
            return

        # Safely detach the existing layout from the widget before creating a new one.
        # Qt will crash if we assign a new layout while one is still installed.
        current_layout = self.pdf_widget.layout()
        if current_layout is not None:
            while current_layout.count():
                item = current_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

            self.pdf_widget.setLayout(None)
            current_layout.deleteLater()

        # Recreate the layout without passing `self.pdf_widget` to the constructor.
        # Then assign it explicitly after detaching the previous layout.
        if self.scroll_mode == "horizontal":
            self.pdf_layout = QHBoxLayout()
        else:
            self.pdf_layout = QVBoxLayout()
        self.pdf_widget.setLayout(self.pdf_layout)

        # Make adjacent pages look "joined" (no gaps/margins between labels).
        self.pdf_layout.setContentsMargins(0, 0, 0, 0)
        self.pdf_layout.setSpacing(0)

    def load_pdf(self, file_path):
        """Loads and displays the PDF with optimized scaling for landscape."""
        self.current_file = file_path
        self.manual_zoom = False  # Reset manual zoom flag
        self.render_pdf()

    def render_pdf(self):
        """Renders the PDF with optimized scaling for landscape orientation."""
        try:
            if not self.current_file:
                return

            # Open the PDF file
            doc = pymupdf.open(self.current_file)
            self.clear_pdf()
            
            # Calculate optimal zoom factor for landscape pages (only if not manual zoom)
            if not self.manual_zoom and len(doc) > 0:
                if self.default_zoom is not None:
                    # Use the provided default zoom
                    self.zoom_factor = self.default_zoom
                else:
                    # Calculate automatic optimal zoom for landscape pages
                    first_page = doc[0]
                    page_width = first_page.rect.width
                    page_height = first_page.rect.height
                    
                    # Calculate zoom factor to fit width
                    if page_width > page_height:  # Landscape
                        # Scale to fit width with some padding
                        available_width = self.target_width - 40  # 20px padding on each side
                        self.zoom_factor = available_width / page_width
                    else:  # Portrait
                        # Scale to fit width but maintain aspect ratio
                        available_width = self.target_width - 40
                        self.zoom_factor = available_width / page_width

            dpi = 72 * self.zoom_factor

            for page_number in range(len(doc)):
                page = doc[page_number]
                matrix = pymupdf.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=matrix)
                image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(image)

                label = QLabel()
                label.setPixmap(pixmap)
                # Keep alignment consistent; layout spacing/margins are what make pages "join".
                label.setAlignment(Qt.AlignCenter)
                label.setMinimumWidth(pixmap.width())
                label.setMinimumHeight(pixmap.height())
                self.pdf_layout.addWidget(label)
                
        except Exception as e:
            print(f"Error rendering PDF: {e}")
            label = QLabel("Unable to load PDF.")
            label.setAlignment(Qt.AlignCenter)
            self.pdf_layout.addWidget(label)

        # Reset the active scrollbar after re-rendering.
        if self.scroll_mode == "horizontal":
            QTimer.singleShot(0, lambda: self.horizontalScrollBar().setValue(0))
        else:
            QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(0))

    def clear_pdf(self):
        """Clears the current PDF view."""
        while self.pdf_layout.count():
            widget = self.pdf_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()

    def set_zoom(self, zoom_factor):
        """Updates the zoom factor and re-renders the PDF."""
        self.zoom_factor = zoom_factor
        self.manual_zoom = True  # Mark as manual zoom
        self.render_pdf()  # Re-render the PDF with the updated zoom factor
        
    def resizeEvent(self, event):
        """Handle window resize to recalculate zoom factor with debouncing."""
        super().resizeEvent(event)
        
        # Only trigger resize if width actually changed significantly
        current_width = self.width()
        if abs(current_width - self.last_width) > 10:  # Only if width changed by more than 10px
            self.last_width = current_width
            self.target_width = current_width - 40  # Account for scrollbar and padding
            
            # Stop any existing timer and start a new one
            self.resize_timer.stop()
            self.resize_timer.start(200)  # 200ms delay to prevent rapid re-renders
            
    def delayed_resize_render(self):
        """Delayed render after resize to prevent shaking."""
        if self.current_file:
            self.manual_zoom = False  # Reset to auto-zoom on resize
            self.render_pdf()