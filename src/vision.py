import cv2
import numpy as np
import time
from tracker import TrackerPelota
from config import *

class VisionSystem:

    def __init__(self, camera_index=0):

        self.cap = cv2.VideoCapture(camera_index)
        self.trackers = []

        # Disco fijo (luego podemos hacerlo dinámico desde GUI)
        self.disco_cx = 320
        self.disco_cy = 240
        self.disco_radio = 220

        self.kernel_opening = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.kernel_closing = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.kernel_negro   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        # Rangos HSV
        self.rangos_hsv = {
            "Verde":    [(np.array([68,123,65]),   np.array([107,255,255]))],
            "Azul":     [(np.array([101,118,102]), np.array([118,239,198]))],
            "Amarillo": [(np.array([21,101,0]),    np.array([41,220,255]))],
            "Rosa":     [(np.array([135,24,150]),  np.array([179,100,255]))],
            "Rojo":     [(np.array([0,102,120]),   np.array([12,255,255])),
                         (np.array([168,102,120]), np.array([179,255,255]))]
        }

    # ==========================================
    # MÁSCARA DISCO
    # ==========================================
    def hacer_mascara_disco(self, shape):
        mask = np.zeros(shape[:2], dtype=np.uint8)
        cv2.circle(mask, (self.disco_cx, self.disco_cy), self.disco_radio, 255, -1)
        return mask

    # ==========================================
    # DETECTAR SECTORES
    # ==========================================
    def detectar_sectores(self, frame_hsv, mascara_disco):

        mascaras = {}

        for nombre, rangos in self.rangos_hsv.items():

            mask = np.zeros(frame_hsv.shape[:2], dtype=np.uint8)

            for (lo, hi) in rangos:
                mask = cv2.bitwise_or(mask, cv2.inRange(frame_hsv, lo, hi))

            mask = cv2.bitwise_and(mask, mascara_disco)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel_opening, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel_closing, iterations=1)

            mascaras[nombre] = mask

        return mascaras

    # ==========================================
    # DETECTAR PELOTAS NEGRAS
    # ==========================================
    def detectar_pelotas(self, frame_hsv, mascara_disco):

        mask_negro = cv2.inRange(frame_hsv, RANGO_NEGRO_LOWER, RANGO_NEGRO_UPPER)
        mask_negro = cv2.bitwise_and(mask_negro, mascara_disco)
        mask_negro = cv2.morphologyEx(mask_negro, cv2.MORPH_OPEN,  self.kernel_negro, iterations=1)
        mask_negro = cv2.morphologyEx(mask_negro, cv2.MORPH_CLOSE, self.kernel_negro, iterations=2)

        cnts, _ = cv2.findContours(mask_negro, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detecciones = []

        for c in cnts:

            area = cv2.contourArea(c)
            if not (AREA_MINIMA_PELOTA_NEGRA < area < AREA_MAXIMA_PELOTA_NEGRA):
                continue

            perimetro = cv2.arcLength(c, True)
            if perimetro == 0:
                continue

            circularidad = (4 * np.pi * area) / (perimetro ** 2)
            if circularidad < CIRCULARIDAD_MINIMA:
                continue

            M = cv2.moments(c)
            if M["m00"] == 0:
                continue

            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            detecciones.append({
                "contorno": c,
                "cx": cx,
                "cy": cy
            })

        return detecciones

    # ==========================================
    # DETERMINAR SECTOR DE LA PELOTA
    # ==========================================
    def obtener_sector(self, pelota_mask, mascaras_sectores):

        mejor_sector = None
        max_solap = 0

        for nombre, mask in mascaras_sectores.items():
            solap = cv2.countNonZero(cv2.bitwise_and(pelota_mask, mask))
            if solap > max_solap:
                max_solap = solap
                mejor_sector = nombre

        return mejor_sector

    # ==========================================
    # TRACKING Y CONFIRMACIÓN
    # ==========================================
    def actualizar_trackers(self, detecciones, mascaras_sectores, frame_shape):

        lanzamiento_valido = False
        puntos = 0

        for det in detecciones:

            mask_pelota = np.zeros(frame_shape[:2], dtype=np.uint8)
            cv2.circle(mask_pelota, (det["cx"], det["cy"]), 20, 255, -1)

            sector = self.obtener_sector(mask_pelota, mascaras_sectores)

            if sector is None:
                continue

            puntos_sector = PUNTUACIONES.get(sector, 0)

            nuevo = TrackerPelota(det["cx"], det["cy"], sector, puntos_sector)
            self.trackers.append(nuevo)

        for t in self.trackers:

            if not t.confirmada and t.tiempo_visible() >= TIEMPO_CONFIRMACION:
                t.confirmada = True
                lanzamiento_valido = True
                puntos = t.puntos
                break

        self.trackers = [t for t in self.trackers if t.tiempo_visible() < TIEMPO_OLVIDO]

        return lanzamiento_valido, puntos

    # ==========================================
    # MÉTODO PRINCIPAL
    # ==========================================
    def get_frame(self):

        ret, frame = self.cap.read()
        if not ret:
            return None, False, 0

        frame = cv2.flip(frame, 1)
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mascara_disco = self.hacer_mascara_disco(frame.shape)

        mascaras_sectores = self.detectar_sectores(frame_hsv, mascara_disco)
        detecciones = self.detectar_pelotas(frame_hsv, mascara_disco)

        lanzamiento_valido, puntos = self.actualizar_trackers(
            detecciones, mascaras_sectores, frame.shape
        )

        # Dibujar disco
        cv2.circle(frame, (self.disco_cx, self.disco_cy), self.disco_radio, (255,255,0), 2)

        # Dibujar detecciones
        for det in detecciones:
            cv2.circle(frame, (det["cx"], det["cy"]), 20, (0,255,0), 2)

        return frame, lanzamiento_valido, puntos