import cv2
import numpy as np

from config import COLORES_BGR, AREA_MINIMA_SECTOR


def dibujar_sectores(frame_display, mascaras):
    for nombre, mascara in mascaras.items():
        color_bgr = COLORES_BGR[nombre]
        cnts, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv2.contourArea(c) > AREA_MINIMA_SECTOR:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    cv2.drawContours(frame_display, [c], -1, color_bgr, 2)
                    cv2.putText(frame_display, nombre, (cx - 20, cy + 25), 1, 0.5, color_bgr, 1)


def dibujar_trackers(frame_display, trackers):
    for t in trackers:
        cx, cy       = t.cx, t.cy
        sector       = t.sector
        color_sector = COLORES_BGR.get(sector, (255, 255, 255))
        color_circ   = (0, 255, 0) if t.confirmada else (255, 255, 255)

        cv2.circle(frame_display, (cx, cy), 30, color_circ, 2)
        cv2.circle(frame_display, (cx, cy),  4, color_circ, -1)

        if t.confirmada:
            cv2.putText(frame_display, f"{sector} +{t.puntos_sumados}",
                        (cx - 40, cy - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_sector, 2)
        else:
            if sector:
                cv2.putText(frame_display, f"{sector}: {t.puntos}pts",
                            (cx - 45, cy - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_sector, 2)
            bw = int(t.progreso() * 60)
            cv2.rectangle(frame_display, (cx - 30, cy + 12), (cx + 30,      cy + 20), (40, 40, 40),    -1)
            cv2.rectangle(frame_display, (cx - 30, cy + 12), (cx - 30 + bw, cy + 20), (0, 220, 0),     -1)
            cv2.rectangle(frame_display, (cx - 30, cy + 12), (cx + 30,      cy + 20), (180, 180, 180),   1)