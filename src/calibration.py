import cv2
import numpy as np


def mouse_callback_factory(app_state):
    """
    Devuelve una funcion de callback de mouse que opera sobre app_state (dict compartido).
    app_state debe tener las claves:
        estado, color_seleccionado, rangos_hsv, frame_hsv_global,
        drag_inicio, drag_actual, disco_cx, disco_cy, disco_radio, disco_listo
    """

    def mouse_callback(event, x, y, flags, param):
        s = app_state

        if s["estado"] == "CALIBRANDO_DISCO":
            if event == cv2.EVENT_LBUTTONDOWN:
                s["drag_inicio"] = (x, y)
                s["drag_actual"] = (x, y)
                s["disco_listo"] = False
            elif event == cv2.EVENT_MOUSEMOVE and s["drag_inicio"]:
                s["drag_actual"] = (x, y)
            elif event == cv2.EVENT_LBUTTONUP and s["drag_inicio"]:
                s["disco_cx"]    = s["drag_inicio"][0]
                s["disco_cy"]    = s["drag_inicio"][1]
                s["disco_radio"] = int(np.sqrt(
                    (x - s["drag_inicio"][0]) ** 2 + (y - s["drag_inicio"][1]) ** 2
                ))
                if s["disco_radio"] > 10:
                    s["disco_listo"] = True
                    print(f"[Disco] Centro=({s['disco_cx']},{s['disco_cy']}) Radio={s['disco_radio']}px")
                s["drag_inicio"] = None

        elif event == cv2.EVENT_LBUTTONDOWN and s["estado"] == "CALIBRANDO_CLIC":
            hsv = s["frame_hsv_global"]
            if hsv is None:
                return
            y_min = max(0, y - 2)
            y_max = min(hsv.shape[0], y + 3)
            x_min = max(0, x - 2)
            x_max = min(hsv.shape[1], x + 3)
            roi = hsv[y_min:y_max, x_min:x_max]
            h, sv, v = np.median(roi, axis=(0, 1)).astype(int)
            T_H, T_S, T_V = 10, 60, 60
            color = s["color_seleccionado"]
            if h < T_H or h > (179 - T_H):
                l1 = np.array([0, max(0, sv - T_S), max(0, v - T_V)])
                u1 = np.array([h + T_H if h < 50 else 10, min(255, sv + T_S), min(255, v + T_V)])
                l2 = np.array([h - T_H if h > 150 else 170, max(0, sv - T_S), max(0, v - T_V)])
                u2 = np.array([179, min(255, sv + T_S), min(255, v + T_V)])
                s["rangos_hsv"][color] = [(l1, u1), (l2, u2)]
            else:
                l = np.array([max(0, h - T_H), max(0, sv - T_S), max(0, v - T_V)])
                u = np.array([min(179, h + T_H), min(255, sv + T_S), min(255, v + T_V)])
                s["rangos_hsv"][color] = [(l, u)]
            print(f"[{color}] HSV: H={h} S={sv} V={v}")
            s["estado"] = "MENU_COLORES"

    return mouse_callback