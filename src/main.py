import sys
import cv2

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame
)
from PyQt6.QtGui import QImage, QPixmap, QFont
from PyQt6.QtCore import QTimer, Qt

from vision import VisionSystem
from system_state import GameState
from esp32_serial import ESP32Controller


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Spinning Disk")
        self.setGeometry(100, 100, 1300, 750)
        self.setStyleSheet("background-color: #0e1117; color: white;")

        self.game = GameState()
        self.vision = VisionSystem(camera_index=1)  # Ajusta si necesario
        self.esp32 = ESP32Controller(port="COM10")

        self.init_ui()

        # Cámara SIEMPRE activa
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    # ---------------- UI ----------------
    def init_ui(self):

        # -------- VIDEO --------
        self.video_label = QLabel()
        self.video_label.setFixedSize(800, 600)
        self.video_label.setStyleSheet("border: 2px solid #1f2937;")

        # -------- PANEL DERECHO --------
        right_panel = QFrame()
        right_panel.setFixedWidth(400)
        right_panel.setStyleSheet("""
            background-color: #111827;
            border-radius: 10px;
            padding: 20px;
        """)

        title = QLabel("Spinning Disk")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.throws_label = QLabel("Lanzamientos válidos: 0")
        self.last_score_label = QLabel("Puntaje último lanzamiento: 0")
        self.total_score_label = QLabel("Puntaje total acumulado: 0")

        for label in [self.throws_label, self.last_score_label, self.total_score_label]:
            label.setFont(QFont("Arial", 12))

        # -------- BOTONES --------
        self.start_button = QPushButton("START")
        self.stop_button = QPushButton("STOP")

        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                padding: 12px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #22c55e;
            }
        """)

        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                padding: 12px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ef4444;
            }
        """)

        self.start_button.clicked.connect(self.start_game)
        self.stop_button.clicked.connect(self.stop_game)

        right_layout = QVBoxLayout()
        right_layout.addWidget(title)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.throws_label)
        right_layout.addWidget(self.last_score_label)
        right_layout.addWidget(self.total_score_label)
        right_layout.addSpacing(30)
        right_layout.addWidget(self.start_button)
        right_layout.addWidget(self.stop_button)
        right_layout.addStretch()

        right_panel.setLayout(right_layout)

        # -------- LAYOUT PRINCIPAL --------
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.video_label)
        main_layout.addWidget(right_panel)

        self.setLayout(main_layout)

    # ---------------- LÓGICA ----------------
    def start_game(self):
        self.game.reset()
        self.game.running = True
        self.esp32.send_start()
        self.update_labels()

    def stop_game(self):
        self.game.running = False
        self.esp32.send_stop()

    def update_labels(self):
        self.throws_label.setText(f"Lanzamientos válidos: {self.game.throws}")
        self.last_score_label.setText(f"Puntaje último lanzamiento: {self.game.last_score}")
        self.total_score_label.setText(f"Puntaje total acumulado: {self.game.total_score}")

    # ---------------- VIDEO ----------------
    def update_frame(self):
        frame = self.vision.get_frame()
        if frame is None:
            return

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w

        qt_image = QImage(
            rgb_image.data,
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )

        self.video_label.setPixmap(QPixmap.fromImage(qt_image))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
