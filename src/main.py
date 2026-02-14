import sys
import cv2
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout
)
from PyQt6.QtGui import QImage, QPixmap, QFont
from PyQt6.QtCore import QTimer, Qt

from vision import VisionSystem
from system_state import GameState
from esp32_serial import ESP32Controller


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Spinning Disk System")
        self.setGeometry(100, 100, 1000, 800)
        self.setStyleSheet("background-color: #1e1e1e;")

        self.game = GameState()
        self.vision = VisionSystem(camera_index=1)
        self.esp32 = ESP32Controller(port="COM10")

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def init_ui(self):

        # =========================
        # TÍTULO
        # =========================
        self.title_label = QLabel("SPINNING DISK")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        font = QFont("Arial", 32, QFont.Weight.Bold)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: white;")

        # =========================
        # BOTONES
        # =========================
        self.start_button = QPushButton("START")
        self.stop_button = QPushButton("STOP")

        self.start_button.setFixedHeight(50)
        self.stop_button.setFixedHeight(50)

        self.start_button.clicked.connect(self.start_game)
        self.stop_button.clicked.connect(self.stop_game)

        # Estilo botón START (verde)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)

        # Estilo botón STOP (rojo)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)

        # =========================
        # VIDEO
        # =========================
        self.video_label = QLabel()
        self.video_label.setFixedSize(800, 600)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: black;
                border: 3px solid #444;
                border-radius: 10px;
            }
        """)

        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # =========================
        # LAYOUT PRINCIPAL
        # =========================
        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addSpacing(20)
        layout.addLayout(button_layout)
        layout.addSpacing(30)
        layout.addWidget(self.video_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    # =========================
    # CONTROL
    # =========================

    def start_game(self):
        self.game.reset()
        self.game.running = True
        self.esp32.send_start()
        self.esp32.send_scores(0, 0, 0)

    def stop_game(self):
        self.game.running = False
        self.esp32.send_stop()

    # =========================
    # VIDEO LOOP
    # =========================

    def update_frame(self):

        frame, lanzamiento_valido, puntos = self.vision.get_frame()

        if frame is None:
            return

        if self.game.running and lanzamiento_valido:

            self.game.add_score(puntos)

            self.esp32.send_scores(
                self.game.throws,
                self.game.last_score,
                self.game.total_score
            )

            if self.game.throws >= 3:
                self.stop_game()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
