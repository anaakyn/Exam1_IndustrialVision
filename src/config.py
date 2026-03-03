import numpy as np

# ==========================================
# PUNTUACIONES
# ==========================================
PUNTUACION_ROSA     = 100
PUNTUACION_AZUL     = 50
PUNTUACION_VERDE    = 40
PUNTUACION_AMARILLO = 25
PUNTUACION_ROJO     = 20

# ==========================================
# PARÁMETROS DE DETECCIÓN
# ==========================================
AREA_MINIMA_SECTOR       = 2000
TIEMPO_CONFIRMACION      = 0.8
MAX_PELOTAS              = 3
DISTANCIA_MISMA_PELOTA   = 120
TIEMPO_OLVIDO            = 4.0

RANGO_NEGRO_LOWER        = np.array([0,   0,   0])
RANGO_NEGRO_UPPER        = np.array([179, 120, 80])
AREA_MINIMA_PELOTA_NEGRA = 500
AREA_MAXIMA_PELOTA_NEGRA = 10000
CIRCULARIDAD_MINIMA      = 0.55

# ==========================================
# RANGOS HSV
# ==========================================
RANGOS_HSV_DEFAULT = {
    "Verde":    [(np.array([68, 123, 65]),   np.array([107, 255, 255]))],
    "Azul":     [(np.array([101, 118, 102]), np.array([118, 239, 198]))],
    "Amarillo": [(np.array([21, 101, 0]),    np.array([41, 220, 255]))],
    "Rosa":     [(np.array([135, 24, 150]),  np.array([179, 100, 255]))],
    "Rojo":     [(np.array([0, 102, 120]),   np.array([12, 255, 255])),
                 (np.array([168, 102, 120]), np.array([179, 255, 255]))]
}

COLORES_BGR = {
    "Verde":    (0, 255, 0),
    "Azul":     (255, 0, 0),
    "Amarillo": (0, 255, 255),
    "Rosa":     (180, 105, 255),
    "Rojo":     (0, 0, 255),
}

PUNTUACIONES = {
    "Verde":    PUNTUACION_VERDE,
    "Azul":     PUNTUACION_AZUL,
    "Amarillo": PUNTUACION_AMARILLO,
    "Rosa":     PUNTUACION_ROSA,
    "Rojo":     PUNTUACION_ROJO,
}

# ==========================================
# ARDUINO
# ==========================================
ARDUINO_PORT = "COM9"
ARDUINO_BAUD = 9600