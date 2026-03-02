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
from serial_controller import ArduinoNanoController


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Spinning Disk System")
        self.setGeometry(100, 100, 1100, 850)
        self.setStyleSheet("background-color: #1e1e1e;")

        # =========================
        # SISTEMAS
        # =========================
        self.game = GameState()
        self.vision = VisionSystem(camera_index=1)
        self.arduino = ArduinoNanoController(port="COM9")

        self.init_ui()

        # Timer de actualización
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    # ==========================================
    # UI
    # ==========================================
    def init_ui(self):

        # ===== TÍTULO =====
        self.title_label = QLabel("SPINNING DISK")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        font = QFont("Arial", 32, QFont.Weight.Bold)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: white;")

        # ===== MARCADOR =====
        self.score_label = QLabel("Throws: 0 | Last: 0 | Total: 0")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setFont(QFont("Arial", 18))
        self.score_label.setStyleSheet("color: #f1c40f;")

        # ===== BOTONES =====
        self.start_button = QPushButton("START")
        self.stop_button = QPushButton("STOP")

        self.start_button.setFixedHeight(50)
        self.stop_button.setFixedHeight(50)

        self.start_button.clicked.connect(self.start_game)
        self.stop_button.clicked.connect(self.stop_game)

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

        # ===== VIDEO =====
        self.video_label = QLabel()
        self.video_label.setFixedSize(900, 650)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: black;
                border: 3px solid #444;
                border-radius: 10px;
            }
        """)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ===== LAYOUT PRINCIPAL =====
        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addSpacing(10)
        layout.addWidget(self.score_label)
        layout.addSpacing(20)
        layout.addLayout(button_layout)
        layout.addSpacing(20)
        layout.addWidget(self.video_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    # ==========================================
    # CONTROL
    # ==========================================
    def start_game(self):
        self.game.reset()
        self.game.running = True
        self.update_score_display()

        self.arduino.send_start()
        self.arduino.send_scores(0, 0, 0)

    def stop_game(self):
        self.game.running = False
        self.arduino.send_stop()

    def update_score_display(self):
        self.score_label.setText(
            f"Throws: {self.game.throws} | "
            f"Last: {self.game.last_score} | "
            f"Total: {self.game.total_score}"
        )

    # ==========================================
    # LOOP VIDEO
    # ==========================================
    def update_frame(self):

        frame, lanzamiento_valido, puntos = self.vision.get_frame()

        if frame is None:
            return

        # Si el juego está activo y hubo lanzamiento válido
        if self.game.running and lanzamiento_valido:

            self.game.add_score(puntos)
            self.update_score_display()

            self.arduino.send_scores(
                self.game.throws,
                self.game.last_score,
                self.game.total_score
            )

            # Limitar a 3 lanzamientos
            if self.game.throws >= 3:
                self.stop_game()

        # Convertir frame a Qt
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    # ==========================================
    # CIERRE SEGURO
    # ==========================================
    def closeEvent(self, event):
        self.arduino.close()
        self.vision.cap.release()
        event.accept()


# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())