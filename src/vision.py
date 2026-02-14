import cv2
import numpy as np

COLORES = {
    "Rojo": {
        "bajo": {"L": np.array([0, 99, 59]), "U": np.array([10, 255, 255])},
        "alto": {"L": np.array([160, 100, 100]), "U": np.array([179, 255, 255])},
        "puntos": 20
    },
    "Azul": {"L": np.array([101, 109, 21]), "U": np.array([147, 255, 255]), "puntos": 50},
    "Verde": {"L": np.array([68, 149, 62]), "U": np.array([104, 255, 255]), "puntos": 25},
    "Amarillo": {"L": np.array([21, 101, 0]), "U": np.array([41, 220, 255]), "puntos": 25},
    "Rosa": {"L": np.array([135, 24, 184]), "U": np.array([179, 57, 255]), "puntos": 40},
}

VISUAL_COLORS = {
    "Rojo": (0, 0, 255),
    "Azul": (255, 0, 0),
    "Verde": (0, 255, 0),
    "Amarillo": (0, 255, 255),
    "Rosa": (180, 105, 255)
}

AREA_MINIMA_ZONA = 6000
AREA_MINIMA_PELOTA = 1200
AREA_MAXIMA_PELOTA = 7000
CIRCULARIDAD_MIN = 0.65
TOLERANCIA_DISTANCIA = -10


class VisionSystem:

    def __init__(self, camera_index=1):
        self.cap = cv2.VideoCapture(camera_index)

        # Memoria para evitar doble conteo
        self.pelota_activa = False
        self.frames_estables = 0
        self.FRAMES_REQUERIDOS = 6

    def get_frame(self):

        ret, frame = self.cap.read()
        if not ret:
            return None, False, 0

        frame = cv2.flip(frame, 1)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        zonas_activas = []
        lanzamiento_valido = False
        puntos_detectados = 0

        # =====================
        # DETECTAR ZONAS COLOR
        # =====================
        for nombre, data in COLORES.items():

            if nombre == "Rojo":
                m1 = cv2.inRange(hsv, data["bajo"]["L"], data["bajo"]["U"])
                m2 = cv2.inRange(hsv, data["alto"]["L"], data["alto"]["U"])
                mask_zona = cv2.add(m1, m2)
            else:
                mask_zona = cv2.inRange(hsv, data["L"], data["U"])

            kernel = np.ones((5,5), np.uint8)
            mask_zona = cv2.morphologyEx(mask_zona, cv2.MORPH_CLOSE, kernel)

            cnts_zona, _ = cv2.findContours(mask_zona, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for c in cnts_zona:
                if cv2.contourArea(c) > AREA_MINIMA_ZONA:
                    cv2.drawContours(frame, [c], -1, VISUAL_COLORS[nombre], 3)
                    zonas_activas.append((nombre, c))

        # =====================
        # DETECCIÓN PELOTA NEGRA
        # =====================
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (9,9), 0)

        # Detectar objetos oscuros
        _, th = cv2.threshold(blur, 60, 255, cv2.THRESH_BINARY_INV)

        kernel = np.ones((7,7), np.uint8)
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel)
        th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)

        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in cnts:

            area = cv2.contourArea(c)
            if area < AREA_MINIMA_PELOTA or area > AREA_MAXIMA_PELOTA:
                continue

            perimetro = cv2.arcLength(c, True)
            if perimetro == 0:
                continue

            circularidad = 4 * np.pi * area / (perimetro ** 2)
            if circularidad < CIRCULARIDAD_MIN:
                continue

            M = cv2.moments(c)
            if M["m00"] == 0:
                continue

            px = int(M["m10"] / M["m00"])
            py = int(M["m01"] / M["m00"])

            mejor_color = None

            for (nombre_zona, contorno_zona) in zonas_activas:
                dist = cv2.pointPolygonTest(contorno_zona, (px, py), True)
                if dist > TOLERANCIA_DISTANCIA:
                    mejor_color = nombre_zona
                    break

            if mejor_color:

                self.frames_estables += 1

                if self.frames_estables >= self.FRAMES_REQUERIDOS and not self.pelota_activa:

                    puntos_detectados = COLORES[mejor_color]["puntos"]
                    lanzamiento_valido = True
                    self.pelota_activa = True

                cv2.drawContours(frame, [c], -1, (0,0,255), 3)

            else:
                self.frames_estables = 0
                self.pelota_activa = False

        return frame, lanzamiento_valido, puntos_detectados
