import sys
import cv2
import numpy as np
import platform
from pyzbar.pyzbar import decode
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QMessageBox

if platform.system() == "Windows":
    import winsound

class QRScannerWindow(QMainWindow):
    qr_scanned = Signal(str)  # ✅ Signal to emit QR string

    def __init__(self):
        super().__init__()
        self.setWindowTitle("QR Code Scanner")
        self.setGeometry(100, 100, 640, 480)

        self.widget = QWidget()
        self.layout = QVBoxLayout()

        self.video_label = QLabel(self)
        self.layout.addWidget(self.video_label)

        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.6)  # ✅ Slight brightness boost

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_video)
        self.timer.start(30)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
        """)

        self.scanned = False  # ✅ Prevent multiple scans

    def preprocess_image(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        adaptive = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY, 11, 2)
        return cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR)
    
    def draw_focus_box(self, frame):
        h, w, _ = frame.shape
        top_left = (w // 2 - 100, h // 2 - 100)
        bottom_right = (w // 2 + 100, h // 2 + 100)
        cv2.rectangle(frame, top_left, bottom_right, (255, 255, 255), 2)

    def update_video(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        
        frame = self.preprocess_image(frame)
        decoded_objects = decode(frame)

        for obj in decoded_objects:
            points = obj.polygon
            if len(points) == 4:
                points = np.array(points, dtype=np.int32)
                cv2.polylines(frame, [points], isClosed=True, color=(0, 255, 0), thickness=2)

            qr_data = obj.data.decode('utf-8')
            print("Scanned QR Data: ", qr_data)
            cv2.putText(frame, qr_data, (obj.rect[0], obj.rect[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            if not self.scanned:
                self.scanned = True
                self.timer.stop()
                self.cap.release()

                if platform.system() == "Windows":
                    winsound.Beep(1000, 200)  # ✅ Beep on success

                self.qr_scanned.emit(qr_data)  # ✅ Emit the QR string
                self.close()
                return
            
        self.draw_focus_box(frame)

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(q_img))

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        event.ignore()
        self.hide()

# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = QRScannerWindow()
#     window.show()
#     sys.exit(app.exec())
