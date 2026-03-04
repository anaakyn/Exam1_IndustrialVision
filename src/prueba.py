import cv2
import numpy as np
import time
import serial

arduino = serial.Serial("COM9", 9600)
time.sleep(2)

# 1. CONFIGURACIÓN DE PUNTOS
puntuacion_rosa     = 100
puntuacion_azul     = 50
puntuacion_verde    = 30
puntuacion_amarillo = 25
puntuacion_rojo     = 20

puntaje_total = 0
throws_count  = 0
last_score    = 0

# 2. PARÁMETROS
AREA_MINIMA_SECTOR = 2000
TIEMPO_CONFIRMACION = 0.5
MAX_PELOTAS = 3
MAX_THROWS  = 3

# Dos pelotas se consideran "la misma" si están a menos de esta distancia.
# ← REDUCIDO de 180 a 90 para no bloquear la 3ª pelota
DISTANCIA_MISMA_PELOTA = 90

# Una pelota confirmada se "olvida" si desaparece más de este tiempo
TIEMPO_OLVIDO = 6.0

# Rango negro MÉTODO 1 (original, rango HSV específico)
RANGO_NEGRO_LOWER        = np.array([98,   0,   0])
RANGO_NEGRO_UPPER        = np.array([118, 125, 109])

# Rango negro MÉTODO 2 (por brillo bajo — robusto sobre fondos cálidos)
RANGO_NEGRO2_LOWER       = np.array([0,   0,   0])
RANGO_NEGRO2_UPPER       = np.array([179, 255, 60])

AREA_MINIMA_PELOTA_NEGRA = 500
AREA_MAXIMA_PELOTA_NEGRA = 10000
CIRCULARIDAD_MINIMA      = 0.55

# 3. CLASE TRACKER DE PELOTA
class TrackerPelota:

    _id_counter = 0

    def __init__(self, cx, cy, sector, puntos):
        TrackerPelota._id_counter += 1
        self.id                = TrackerPelota._id_counter
        self.cx                = cx
        self.cy                = cy
        self.sector            = sector
        self.puntos            = puntos
        self.tiempo_inicio     = time.time()
        self.ultima_vez_vista  = time.time()
        self.confirmada        = False
        self.puntos_sumados    = 0

    def actualizar(self, cx, cy, sector, puntos):
        self.cx               = cx
        self.cy               = cy
        self.sector           = sector
        self.puntos           = puntos
        self.ultima_vez_vista = time.time()

    def tiempo_visible(self):
        return time.time() - self.tiempo_inicio

    def ausencia(self):
        return time.time() - self.ultima_vez_vista

    def progreso(self):
        return min(self.tiempo_visible() / TIEMPO_CONFIRMACION, 1.0)

# 4. VARIABLES GLOBALES DE ESTADO
estado             = "MENU_INICIAL"
color_seleccionado = ""
frame_hsv_global   = None
frames_calibracion = 0
MAX_FRAMES_CALIB   = 30

puntaje_total  = 0
trackers       = []
posiciones_confirmadas = []  # (cx, cy) de pelotas ya contadas, persisten toda la partida

# Disco manual
disco_cx    = 0
disco_cy    = 0
disco_radio = 0
disco_listo = False
drag_inicio = None
drag_actual = None

# 5. KERNELS
kernel_opening = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
kernel_closing = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
kernel_negro   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

# 6. RANGOS HSV
rangos_hsv = {
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
    "Verde":    puntuacion_verde,
    "Azul":     puntuacion_azul,
    "Amarillo": puntuacion_amarillo,
    "Rosa":     puntuacion_rosa,
    "Rojo":     puntuacion_rojo,
}

# 7. MÁSCARA DISCO MANUAL
def hacer_mascara_disco(shape, cx, cy, radio):
    mask = np.zeros(shape[:2], dtype=np.uint8)
    cv2.circle(mask, (cx, cy), radio, 255, -1)
    return mask

# 8. CALLBACK RATÓN
def mouse_callback(event, x, y, flags, param):
    global drag_inicio, drag_actual, disco_cx, disco_cy, disco_radio, disco_listo
    global frame_hsv_global, color_seleccionado, rangos_hsv, estado

    if estado == "CALIBRANDO_DISCO":
        if event == cv2.EVENT_LBUTTONDOWN:
            drag_inicio = (x, y)
            drag_actual = (x, y)
            disco_listo = False
        elif event == cv2.EVENT_MOUSEMOVE and drag_inicio:
            drag_actual = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and drag_inicio:
            disco_cx    = drag_inicio[0]
            disco_cy    = drag_inicio[1]
            disco_radio = int(np.sqrt((x-drag_inicio[0])**2 + (y-drag_inicio[1])**2))
            if disco_radio > 10:
                disco_listo = True
                print(f"[Disco] Centro=({disco_cx},{disco_cy}) Radio={disco_radio}px")
            drag_inicio = None

    elif event == cv2.EVENT_LBUTTONDOWN and estado == "CALIBRANDO_CLIC":
        y_min, y_max = max(0, y-2), min(frame_hsv_global.shape[0], y+3)
        x_min, x_max = max(0, x-2), min(frame_hsv_global.shape[1], x+3)
        roi = frame_hsv_global[y_min:y_max, x_min:x_max]
        h, s, v = np.median(roi, axis=(0,1)).astype(int)
        T_H, T_S, T_V = 10, 60, 60

        # Calibración especial para negros
        if color_seleccionado == "NegroNormal":
            global RANGO_NEGRO_LOWER, RANGO_NEGRO_UPPER
            RANGO_NEGRO_LOWER = np.array([max(0,h-T_H),   max(0,s-T_S),   max(0,v-T_V)])
            RANGO_NEGRO_UPPER = np.array([min(179,h+T_H), min(255,s+T_S), min(255,v+T_V)])
            print(f"[NegroNormal] HSV: H={h} S={s} V={v} → Lower={RANGO_NEGRO_LOWER} Upper={RANGO_NEGRO_UPPER}")
            estado = "MENU_COLORES"
            return

        elif color_seleccionado == "NegroCalido":
            global RANGO_NEGRO2_LOWER, RANGO_NEGRO2_UPPER
            RANGO_NEGRO2_LOWER = np.array([max(0,h-T_H),   max(0,s-T_S),   max(0,v-T_V)])
            RANGO_NEGRO2_UPPER = np.array([min(179,h+T_H), min(255,s+T_S), min(255,v+T_V)])
            print(f"[NegroCalido] HSV: H={h} S={s} V={v} → Lower={RANGO_NEGRO2_LOWER} Upper={RANGO_NEGRO2_UPPER}")
            estado = "MENU_COLORES"
            return

        # Calibración normal de colores de sector
        if h < T_H or h > (179 - T_H):
            l1 = np.array([0, max(0,s-T_S), max(0,v-T_V)])
            u1 = np.array([h+T_H if h<50 else 10, min(255,s+T_S), min(255,v+T_V)])
            l2 = np.array([h-T_H if h>150 else 170, max(0,s-T_S), max(0,v-T_V)])
            u2 = np.array([179, min(255,s+T_S), min(255,v+T_V)])
            rangos_hsv[color_seleccionado] = [(l1,u1),(l2,u2)]
        else:
            l = np.array([max(0,h-T_H), max(0,s-T_S), max(0,v-T_V)])
            u = np.array([min(179,h+T_H), min(255,s+T_S), min(255,v+T_V)])
            rangos_hsv[color_seleccionado] = [(l,u)]
        print(f"[{color_seleccionado}] HSV: H={h} S={s} V={v}")
        estado = "MENU_COLORES"

# 9. MORFOLOGÍA
def aplicar_morfologia(mascara, mascara_disco):
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN,  kernel_opening, iterations=2)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel_closing,  iterations=1)
    if mascara_disco is not None:
        mascara = cv2.bitwise_and(mascara, mascara_disco)
    return mascara

# 10. DETECTAR TODAS LAS PELOTAS NEGRAS
def detectar_pelotas_negras(frame_hsv, mascaras_raw, mascara_disco):

    if mascara_disco is None:
        return []

    # Método 1: rango negro original
    mask_negro1 = cv2.inRange(frame_hsv, RANGO_NEGRO_LOWER, RANGO_NEGRO_UPPER)

    # Método 2: negro cálido — restar todos los sectores para evitar falsos positivos
    mask_negro2 = cv2.inRange(frame_hsv, RANGO_NEGRO2_LOWER, RANGO_NEGRO2_UPPER)
    mask_sectores = np.zeros(frame_hsv.shape[:2], dtype=np.uint8)
    for rangos in mascaras_raw.values():
        mask_sectores = cv2.bitwise_or(mask_sectores, rangos)
    mask_negro2 = cv2.bitwise_and(mask_negro2, cv2.bitwise_not(mask_sectores))

    mask_negro = cv2.bitwise_or(mask_negro1, mask_negro2)

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

        # Sector con mayor solapamiento
        color_sector = None
        max_solap    = 0
        mask_pelota  = np.zeros(frame_hsv.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask_pelota, [c], -1, 255, -1)
        for nombre, m_raw in mascaras_raw.items():
            m_dil = cv2.dilate(m_raw, kernel_negro, iterations=10)
            m_dil = cv2.bitwise_and(m_dil, mascara_disco)
            solap = cv2.countNonZero(cv2.bitwise_and(mask_pelota, m_dil))
            if solap > max_solap:
                max_solap    = solap
                color_sector = nombre

        area_norm = (area - AREA_MINIMA_PELOTA_NEGRA) / (AREA_MAXIMA_PELOTA_NEGRA - AREA_MINIMA_PELOTA_NEGRA)
        score = circularidad * 0.6 + area_norm * 0.4

        candidatas.append({
            "contorno":     c,
            "cx":           cx,
            "cy":           cy,
            "color_sector": color_sector,
            "puntos":       PUNTUACIONES.get(color_sector, 0) if color_sector else 0,
            "score":        score,
            "circularidad": round(circularidad, 2),
        })

    candidatas.sort(key=lambda x: x["score"], reverse=True)
    return candidatas[:MAX_PELOTAS]

# 11. ACTUALIZAR TRACKERS (asociación por distancia mínima)
def actualizar_trackers(detecciones):

    global trackers, puntaje_total, throws_count, last_score, posiciones_confirmadas

    trackers_actualizados = set()
    detecciones_asignadas = set()

    if trackers and detecciones:
        matriz = []
        for det in detecciones:
            fila = []
            for t in trackers:
                d = np.sqrt((det["cx"]-t.cx)**2 + (det["cy"]-t.cy)**2)
                fila.append(d)
            matriz.append(fila)

        while True:
            min_dist = float('inf')
            best_i = best_j = -1
            for i, fila in enumerate(matriz):
                if i in detecciones_asignadas:
                    continue
                for j, d in enumerate(fila):
                    t = trackers[j]
                    if t.id in trackers_actualizados:
                        continue
                    if d < min_dist:
                        min_dist = d
                        best_i, best_j = i, j

            if best_i == -1 or min_dist > DISTANCIA_MISMA_PELOTA:
                break

            det = detecciones[best_i]
            t   = trackers[best_j]
            t.actualizar(det["cx"], det["cy"], det["color_sector"], det["puntos"])
            trackers_actualizados.add(t.id)
            detecciones_asignadas.add(best_i)

            # ← FIX: confirmación también funciona cuando throws_count == MAX_THROWS - 1
            if not t.confirmada and t.tiempo_visible() >= TIEMPO_CONFIRMACION and throws_count < MAX_THROWS:
                t.confirmada     = True
                t.puntos_sumados = det["puntos"]

                last_score      = det["puntos"]
                puntaje_total  += det["puntos"]
                throws_count   += 1

                posiciones_confirmadas.append((det["cx"], det["cy"]))

                print(f"✔ Pelota #{t.id} en {det['color_sector']} +{det['puntos']}pts | Total: {puntaje_total} | Lanzamiento: {throws_count}/{MAX_THROWS}")

                mensaje = f"{throws_count},{last_score},{puntaje_total}\n"
                arduino.write(mensaje.encode())

    # ← FIX: usar margen reducido (90px) para no bloquear la 3ª pelota
    for i, det in enumerate(detecciones):
        if i not in detecciones_asignadas and len(trackers) < MAX_PELOTAS and throws_count < MAX_THROWS:
            cerca_de_confirmada = any(
                np.sqrt((det["cx"]-px)**2 + (det["cy"]-py)**2) < DISTANCIA_MISMA_PELOTA
                for (px, py) in posiciones_confirmadas
            )
            if not cerca_de_confirmada:
                nuevo = TrackerPelota(det["cx"], det["cy"], det["color_sector"], det["puntos"])
                trackers.append(nuevo)
                print(f"+ Nueva pelota #{nuevo.id} en {det['color_sector']}")

    trackers = [t for t in trackers if t.ausencia() < TIEMPO_OLVIDO]

# 12. HELPER
def distancia(p1, p2):
    return np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def reset_juego():
    global puntaje_total, throws_count, last_score, trackers, posiciones_confirmadas

    puntaje_total = 0
    throws_count  = 0
    last_score    = 0
    trackers.clear()
    posiciones_confirmadas.clear()
    TrackerPelota._id_counter = 0

    print("RESET DESDE BOTON START")

# 13. LOOP PRINCIPAL
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
cv2.namedWindow("Deteccion Rotatoria Dinamica")
cv2.setMouseCallback("Deteccion Rotatoria Dinamica", mouse_callback)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if arduino.in_waiting > 0:
        mensaje = arduino.readline().decode().strip()
        if mensaje == "START":
            reset_juego()

    frame            = cv2.flip(frame, 1)
    frame_hsv_global = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    frame_display    = frame.copy()
    key              = cv2.waitKey(1) & 0xFF

    mascara_disco = hacer_mascara_disco(frame.shape, disco_cx, disco_cy, disco_radio) \
                    if disco_listo else None

    # MÁQUINA DE ESTADOS

    if estado == "MENU_INICIAL":
        cv2.putText(frame_display, "MENU PRINCIPAL", (20,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
        cv2.putText(frame_display, "1. Definir disco y jugar", (20,100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame_display, "2. Configurar colores", (20,140), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        if   key == ord('1'): estado = "CALIBRANDO_DISCO"
        elif key == ord('2'): estado = "MENU_COLORES"
        elif key == ord('q'): break

    elif estado == "MENU_COLORES":
        cv2.putText(frame_display, "SELECCIONA COLOR A CALIBRAR:", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)
        cv2.putText(frame_display, "1: Verde | 2: Azul | 3: Amarillo", (20,90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame_display, "4: Rosa  | 5: Rojo", (20,130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame_display, "6: Negro normal  | 7: Negro calido", (20,170), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,200), 2)
        cv2.putText(frame_display, "ESPACIO = volver", (20,215), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        if   key == ord('1'): color_seleccionado="Verde";        estado="CALIBRANDO_CLIC"
        elif key == ord('2'): color_seleccionado="Azul";         estado="CALIBRANDO_CLIC"
        elif key == ord('3'): color_seleccionado="Amarillo";     estado="CALIBRANDO_CLIC"
        elif key == ord('4'): color_seleccionado="Rosa";         estado="CALIBRANDO_CLIC"
        elif key == ord('5'): color_seleccionado="Rojo";         estado="CALIBRANDO_CLIC"
        elif key == ord('6'): color_seleccionado="NegroNormal";  estado="CALIBRANDO_CLIC"
        elif key == ord('7'): color_seleccionado="NegroCalido";  estado="CALIBRANDO_CLIC"
        elif key == 32:       estado="MENU_INICIAL"

    elif estado == "CALIBRANDO_CLIC":
        cv2.putText(frame_display, f"CALIBRANDO: {color_seleccionado.upper()}", (20,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
        cv2.putText(frame_display, "Haz CLIC sobre ese color", (20,100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame_display, "'c' para cancelar", (20,140), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
        if key == ord('c'): estado = "MENU_COLORES"

    elif estado == "CALIBRANDO_DISCO":
        cv2.putText(frame_display, "DEFINE EL DISCO", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,255), 2)
        cv2.putText(frame_display, "CLIC en el centro, ARRASTRA al borde", (20,80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        cv2.putText(frame_display, "ESPACIO = confirmar  |  'r' = reintentar", (20,115), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,0), 2)

        if drag_inicio and drag_actual:
            r_prev = int(distancia(drag_inicio, drag_actual))
            cv2.circle(frame_display, drag_inicio, 5, (0,255,255), -1)
            cv2.circle(frame_display, drag_inicio, r_prev, (0,255,255), 2)
            cv2.putText(frame_display, f"radio: {r_prev}px",
                        (drag_inicio[0]+10, drag_inicio[1]-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,255), 2)
        elif disco_listo:
            cv2.circle(frame_display, (disco_cx,disco_cy), disco_radio, (0,255,0), 2)
            cv2.circle(frame_display, (disco_cx,disco_cy), 5, (0,255,0), -1)
            cv2.putText(frame_display, f"r={disco_radio}px  OK — ESPACIO para jugar",
                        (20, frame_display.shape[0]-20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

        if key == 32 and disco_listo:
            estado = "JUEGO"
            trackers.clear()
            print(f"[Disco OK] Centro=({disco_cx},{disco_cy}) Radio={disco_radio}px")
        elif key == ord('r'):
            disco_listo = False; drag_inicio = None; drag_actual = None

    # JUEGO
    elif estado == "JUEGO":

        # Máscaras RAW
        mascaras_raw = {}
        for nombre, rangos in rangos_hsv.items():
            m = np.zeros(frame_hsv_global.shape[:2], dtype=np.uint8)
            for (lo, hi) in rangos:
                m = cv2.bitwise_or(m, cv2.inRange(frame_hsv_global, lo, hi))
            mascaras_raw[nombre] = m

        # Máscaras procesadas limitadas al disco
        mascaras = {n: aplicar_morfologia(m.copy(), mascara_disco)
                    for n, m in mascaras_raw.items()}

        # Borde del disco
        if disco_listo:
            cv2.circle(frame_display, (disco_cx,disco_cy), disco_radio, (255,255,0), 2)

        # Dibujar sectores
        for nombre, mascara in mascaras.items():
            color_bgr = COLORES_BGR[nombre]
            cnts, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                if cv2.contourArea(c) > AREA_MINIMA_SECTOR:
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"]/M["m00"])
                        cy = int(M["m01"]/M["m00"])
                        cv2.drawContours(frame_display, [c], -1, color_bgr, 2)
                        cv2.putText(frame_display, nombre, (cx-20,cy+25), 1, 0.5, color_bgr, 1)

        # ← FIX PRINCIPAL: detectar SIEMPRE, independiente de throws_count
        # Así la 3ª pelota puede ser trackeada mientras está en vuelo
        detecciones = detectar_pelotas_negras(frame_hsv_global, mascaras_raw, mascara_disco)

        # Solo actualizar trackers si no se alcanzó el límite
        if throws_count < MAX_THROWS:
            actualizar_trackers(detecciones)

        # Dibujar cada tracker (incluyendo pelotas ya confirmadas)
        for t in trackers:
            cx, cy       = t.cx, t.cy
            sector       = t.sector
            color_sector = COLORES_BGR.get(sector, (255, 255, 255))
            color_circ   = (0, 255, 0) if t.confirmada else (255, 255, 255)

            cv2.circle(frame_display, (cx, cy), 30, color_circ, 2)
            cv2.circle(frame_display, (cx, cy),  4, color_circ, -1)

            if sector:
                cv2.putText(frame_display, f"{sector}",
                            (cx-30, cy-35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_sector, 2)

        # Teclas
        if key == ord('d'):
            estado = "CALIBRANDO_DISCO"; disco_listo = False
        elif key == ord('r'):
            reset_juego()
            print("♻ Reset completo")
        elif key == ord('m'):
            estado = "MENU_INICIAL"

    cv2.imshow("Deteccion Rotatoria Dinamica", frame_display)
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()