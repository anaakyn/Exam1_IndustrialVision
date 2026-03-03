import cv2
import numpy as np

from config import (
    RANGO_NEGRO_LOWER, RANGO_NEGRO_UPPER,
    AREA_MINIMA_PELOTA_NEGRA, AREA_MAXIMA_PELOTA_NEGRA,
    CIRCULARIDAD_MINIMA, MAX_PELOTAS,
)

# ==========================================
# KERNELS
# ==========================================
kernel_opening = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
kernel_closing = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
kernel_negro   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))


def hacer_mascara_disco(shape, cx, cy, radio):
    mask = np.zeros(shape[:2], dtype=np.uint8)
    cv2.circle(mask, (cx, cy), radio, 255, -1)
    return mask


def aplicar_morfologia(mascara, mascara_disco):
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN,  kernel_opening, iterations=2)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel_closing,  iterations=1)
    if mascara_disco is not None:
        mascara = cv2.bitwise_and(mascara, mascara_disco)
    return mascara


def detectar_pelotas_negras(frame_hsv, mascaras_raw, mascara_disco):
    if mascara_disco is None:
        return []

    mask_negro = cv2.inRange(frame_hsv, RANGO_NEGRO_LOWER, RANGO_NEGRO_UPPER)
    mask_negro = cv2.bitwise_and(mask_negro, mascara_disco)
    mask_negro = cv2.morphologyEx(mask_negro, cv2.MORPH_OPEN,  kernel_negro, iterations=1)
    mask_negro = cv2.morphologyEx(mask_negro, cv2.MORPH_CLOSE, kernel_negro, iterations=2)

    cnts, _ = cv2.findContours(mask_negro, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidatas = []
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

        # Determinar sector por mayor solapamiento
        color_sector = None
        max_solap    = 0

        mask_pelota = np.zeros(frame_hsv.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask_pelota, [c], -1, 255, -1)

        for nombre, m_raw in mascaras_raw.items():
            m_dil = cv2.dilate(m_raw, kernel_negro, iterations=6)
            m_dil = cv2.bitwise_and(m_dil, mascara_disco)
            solap = cv2.countNonZero(cv2.bitwise_and(mask_pelota, m_dil))

            if solap > max_solap:
                max_solap    = solap
                color_sector = nombre

        area_norm = (
            (area - AREA_MINIMA_PELOTA_NEGRA)
            / (AREA_MAXIMA_PELOTA_NEGRA - AREA_MINIMA_PELOTA_NEGRA)
        )
        score = circularidad * 0.6 + area_norm * 0.4

        candidatas.append({
            "contorno":     c,
            "cx":           cx,
            "cy":           cy,
            "color_sector": color_sector,
            "score":        score,
            "circularidad": round(circularidad, 2),
        })

    candidatas.sort(key=lambda x: x["score"], reverse=True)
    return candidatas[:MAX_PELOTAS]