import cv2
import numpy as np
import serial
import time
import copy

from config import ARDUINO_PORT, ARDUINO_BAUD, RANGOS_HSV_DEFAULT
from detection import hacer_mascara_disco, aplicar_morfologia, detectar_pelotas_negras
from tracking_manager import TrackingManager
from game_manager import GameManager
from renderer import dibujar_sectores, dibujar_trackers
from calibration import mouse_callback_factory
from app_state import AppState


# ==========================================
# CONEXION ARDUINO
# ==========================================
arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD)
time.sleep(2)

# ==========================================
# ESTADO DE LA APP
# ==========================================
app_state = AppState(copy.deepcopy(RANGOS_HSV_DEFAULT))

# ==========================================
# MANAGERS
# ==========================================
tm = TrackingManager()
game_manager = GameManager(arduino)

# ==========================================
# CAPTURA
# ==========================================
cap = cv2.VideoCapture(1)
VENTANA = "Deteccion Rotatoria Dinamica"
cv2.namedWindow(VENTANA)
cv2.setMouseCallback(VENTANA, mouse_callback_factory(app_state))


def distancia(p1, p2):
    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


# ==========================================
# LOOP PRINCIPAL
# ==========================================
while True:

    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    app_state.frame_hsv_global = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    frame_display = frame.copy()
    key = cv2.waitKey(1) & 0xFF

    s = app_state

    mascara_disco = (
        hacer_mascara_disco(frame.shape, s.disco_cx, s.disco_cy, s.disco_radio)
        if s.disco_listo else None
    )

    # =====================================
    # MAQUINA DE ESTADOS
    # =====================================

    if s.estado == "MENU_INICIAL":

        cv2.putText(frame_display, "MENU PRINCIPAL", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(frame_display, "1. Definir disco y jugar", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame_display, "2. Configurar colores", (20, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if key == ord('1'):
            s.estado = "CALIBRANDO_DISCO"
        elif key == ord('2'):
            s.estado = "MENU_COLORES"
        elif key == ord('q'):
            break

    elif s.estado == "MENU_COLORES":

        cv2.putText(frame_display, "SELECCIONA COLOR A CALIBRAR:", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame_display, "1: Verde | 2: Azul | 3: Amarillo", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame_display, "4: Rosa  | 5: Rojo", (20, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame_display, "ESPACIO = volver", (20, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if key == ord('1'):
            s.color_seleccionado = "Verde";    s.estado = "CALIBRANDO_CLIC"
        elif key == ord('2'):
            s.color_seleccionado = "Azul";     s.estado = "CALIBRANDO_CLIC"
        elif key == ord('3'):
            s.color_seleccionado = "Amarillo"; s.estado = "CALIBRANDO_CLIC"
        elif key == ord('4'):
            s.color_seleccionado = "Rosa";     s.estado = "CALIBRANDO_CLIC"
        elif key == ord('5'):
            s.color_seleccionado = "Rojo";     s.estado = "CALIBRANDO_CLIC"
        elif key == 32:
            s.estado = "MENU_INICIAL"

    elif s.estado == "CALIBRANDO_CLIC":

        cv2.putText(frame_display, f"CALIBRANDO: {s.color_seleccionado.upper()}", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(frame_display, "Haz CLIC sobre ese color", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame_display, "'c' para cancelar", (20, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if key == ord('c'):
            s.estado = "MENU_COLORES"

    elif s.estado == "CALIBRANDO_DISCO":

        cv2.putText(frame_display, "DEFINE EL DISCO", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        cv2.putText(frame_display, "CLIC en el centro, ARRASTRA al borde", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame_display, "ESPACIO = confirmar  |  'r' = reintentar", (20, 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        # Mostrar circulo mientras se arrastra
        if s.drag_inicio and s.drag_actual:
            r_prev = int(distancia(s.drag_inicio, s.drag_actual))
            cv2.circle(frame_display, s.drag_inicio, 5, (0, 255, 255), -1)
            cv2.circle(frame_display, s.drag_inicio, r_prev, (0, 255, 255), 2)
            cv2.putText(frame_display, f"radio: {r_prev}px",
                        (s.drag_inicio[0] + 10, s.drag_inicio[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        elif s.disco_listo:
            cv2.circle(frame_display, (s.disco_cx, s.disco_cy), s.disco_radio, (0, 255, 0), 2)
            cv2.circle(frame_display, (s.disco_cx, s.disco_cy), 5, (0, 255, 0), -1)
            cv2.putText(frame_display, f"r={s.disco_radio}px  OK - ESPACIO para jugar",
                        (20, frame_display.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if key == 32 and s.disco_listo:
            s.estado = "JUEGO"
            tm.reset()
            game_manager.reset()
        elif key == ord('r'):
            s.disco_listo = False
            s.drag_inicio = None
            s.drag_actual = None

    elif s.estado == "JUEGO":

        game_manager.leer_serial(tm)

        mascaras_raw = {}
        for nombre, rangos in s.rangos_hsv.items():
            m = np.zeros(s.frame_hsv_global.shape[:2], dtype=np.uint8)
            for (lo, hi) in rangos:
                m = cv2.bitwise_or(m, cv2.inRange(s.frame_hsv_global, lo, hi))
            mascaras_raw[nombre] = m

        mascaras = {
            n: aplicar_morfologia(m.copy(), mascara_disco)
            for n, m in mascaras_raw.items()
        }

        if s.disco_listo:
            cv2.circle(frame_display, (s.disco_cx, s.disco_cy), s.disco_radio, (255, 255, 0), 2)

        dibujar_sectores(frame_display, mascaras)

        detecciones = detectar_pelotas_negras(
            s.frame_hsv_global, mascaras_raw, mascara_disco
        )

        eventos = tm.actualizar(detecciones)

        for evento in eventos:
            game_manager.registrar_evento(evento["sector"])

        dibujar_trackers(frame_display, tm.trackers)

        if key == ord('r'):
            tm.reset()
            game_manager.reset()
        elif key == ord('m'):
            s.estado = "MENU_INICIAL"

    cv2.imshow(VENTANA, frame_display)

    if key == ord('q'):
        break


cap.release()
cv2.destroyAllWindows()