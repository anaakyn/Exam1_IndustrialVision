import cv2
import numpy as np

# Tolerancias para expandir el rango automáticamente a partir del clic
TOLERANCIA_H = 10  # Rango de color (Matiz)
TOLERANCIA_S = 60  # Rango de saturación
TOLERANCIA_V = 60  # Rango de brillo

colores_calibrados = {}
nombre_color_actual = "Color_1"
frame_hsv = None

def auto_calibrar(event, x, y, flags, param):
    global frame_hsv, colores_calibrados, nombre_color_actual
    
    # Cuando se hace clic izquierdo en la ventana original
    if event == cv2.EVENT_LBUTTONDOWN:
        # Tomar un área de 5x5 alrededor del clic para evitar píxeles con ruido
        y_min, y_max = max(0, y-2), min(frame_hsv.shape[0], y+3)
        x_min, x_max = max(0, x-2), min(frame_hsv.shape[1], x+3)
        roi = frame_hsv[y_min:y_max, x_min:x_max]

        # Obtener el promedio de HSV (usamos la mediana para mayor precisión)
        promedio_hsv = np.median(roi, axis=(0, 1)).astype(int)
        h, s, v = promedio_hsv

        print(f"\nDetectado HSV promedio en el clic: [H:{h}, S:{s}, V:{v}]")

        # Lógica especial para el Rojo (Wrap-around en H: cerca del 0 o del 179)
        if h < TOLERANCIA_H or h > (179 - TOLERANCIA_H):
            print("¡Color en los extremos detectado (Probablemente Rojo)! Creando rango doble...")
            
            # Rango 1 (Rojo bajo: 0 al 10 aprox)
            lower1 = np.array([0, max(0, s - TOLERANCIA_S), max(0, v - TOLERANCIA_V)])
            upper1 = np.array([h + TOLERANCIA_H if h < 50 else 10, min(255, s + TOLERANCIA_S), min(255, v + TOLERANCIA_V)])
            
            # Rango 2 (Rojo alto: 170 al 179 aprox)
            lower2 = np.array([h - TOLERANCIA_H if h > 150 else 170, max(0, s - TOLERANCIA_S), max(0, v - TOLERANCIA_V)])
            upper2 = np.array([179, min(255, s + TOLERANCIA_S), min(255, v + TOLERANCIA_V)])
            
            # Guardamos dos rangos para este color
            colores_calibrados[nombre_color_actual] = [(lower1, upper1), (lower2, upper2)]
        else:
            # Lógica normal para los demás colores (Verde, Azul, Amarillo, etc.)
            lower = np.array([max(0, h - TOLERANCIA_H), max(0, s - TOLERANCIA_S), max(0, v - TOLERANCIA_V)])
            upper = np.array([min(179, h + TOLERANCIA_H), min(255, s + TOLERANCIA_S), min(255, v + TOLERANCIA_V)])
            
            # Guardamos un solo rango
            colores_calibrados[nombre_color_actual] = [(lower, upper)]
            
        print(f"Rango guardado exitosamente para: {nombre_color_actual}")

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Crear ventana y asignar la función del ratón
cv2.namedWindow('Webcam Original')
cv2.setMouseCallback('Webcam Original', auto_calibrar)

print("--- MODO AUTO-CALIBRACIÓN POR CLIC ---")
print("1. Haz CLIC IZQUIERDO sobre el color que quieres aislar en la ventana 'Webcam Original'.")
print("2. Presiona 'n' para guardar otro color diferente (cambiará de Color_1 a Color_2, etc.).")
print("3. Presiona 'q' para salir e imprimir los arrays generados.")

contador_colores = 1

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Mostrar la máscara del color actual calibrado (si ya hicimos clic)
    if nombre_color_actual in colores_calibrados:
        rangos = colores_calibrados[nombre_color_actual]
        
        # Iniciar máscara vacía
        mask = np.zeros(frame_hsv.shape[:2], dtype=np.uint8)
        
        # Iterar sobre los rangos (será 1 para colores normales, 2 si es rojo)
        for (lower, upper) in rangos:
            mask_temp = cv2.inRange(frame_hsv, lower, upper)
            mask = cv2.bitwise_or(mask, mask_temp) # Unir máscaras
        
        resultado = cv2.bitwise_and(frame, frame, mask=mask)
        cv2.imshow('Mascara Actual', mask)
        cv2.imshow('Resultado Actual', resultado)

    # Mostrar instrucciones en el video
    cv2.putText(frame, f"Calibrando: {nombre_color_actual} (Clic en pantalla)", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imshow('Webcam Original', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('n'):
        contador_colores += 1
        nombre_color_actual = f"Color_{contador_colores}"
        print(f"\nCambiando a nuevo objetivo... Ahora calibrando: {nombre_color_actual}")

cap.release()
cv2.destroyAllWindows()

# Imprimir el código listo para copiar y pegar
print("\n" + "="*50)
print("VALORES FINALES OBTENIDOS LISTOS PARA TU CÓDIGO:")
print("="*50)
for nombre, rangos in colores_calibrados.items():
    print(f"\n# Valores para {nombre}:")
    if len(rangos) == 1:
        print(f"lower_{nombre.lower()} = np.array({rangos[0][0].tolist()})")
        print(f"upper_{nombre.lower()} = np.array({rangos[0][1].tolist()})")
    else:
        print(f"# (ATENCIÓN: Color en bordes del espectro. Requiere sumar máscaras cv2.bitwise_or)")
        print(f"lower1_{nombre.lower()} = np.array({rangos[0][0].tolist()})")
        print(f"upper1_{nombre.lower()} = np.array({rangos[0][1].tolist()})")
        print(f"lower2_{nombre.lower()} = np.array({rangos[1][0].tolist()})")
        print(f"upper2_{nombre.lower()} = np.array({rangos[1][1].tolist()})")
print("="*50)