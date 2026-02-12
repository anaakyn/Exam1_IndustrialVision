import cv2
import numpy as np


COLORES = {
    "Rojo": {
        "bajo": {"L": np.array([0, 100, 100]), "U": np.array([10, 255, 255])},
        "alto": {"L": np.array([160, 100, 100]), "U": np.array([179, 255, 255])}
    },
    "Azul": {"L": np.array([101, 109, 21]), "U": np.array([147, 255, 255])},
    "Verde": {"L": np.array([38, 26, 82]), "U": np.array([93, 255, 236])},
    "Amarillo": {"L": np.array([21, 101, 0]), "U": np.array([41, 220, 255])},
    "Rosa": {"L": np.array([0, 28, 240]), "U": np.array([15, 95, 255])}
}


class VisionSystem:

    def __init__(self, camera_index=1):
        self.cap = cv2.VideoCapture(camera_index)

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None

        frame = cv2.flip(frame, 1)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        frame_final = frame.copy()

        for nombre, rango in COLORES.items():

            if nombre == "Rojo":
                m1 = cv2.inRange(hsv, rango["bajo"]["L"], rango["bajo"]["U"])
                m2 = cv2.inRange(hsv, rango["alto"]["L"], rango["alto"]["U"])
                mask = cv2.add(m1, m2)
            else:
                mask = cv2.inRange(hsv, rango["L"], rango["U"])

            kernel = np.ones((5,5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for c in cnts:
                area = cv2.contourArea(c)
                if area > 1000:
                    cv2.drawContours(frame_final, [c], -1, (0, 255, 0), 3)

                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        cv2.putText(frame_final, nombre, (cx-30, cy),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                    (255, 255, 255), 2)

        return frame_final
