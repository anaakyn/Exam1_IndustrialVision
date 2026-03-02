import numpy as np

from config import DISTANCIA_MISMA_PELOTA, TIEMPO_OLVIDO, MAX_PELOTAS, TIEMPO_CONFIRMACION
from tracker import TrackerPelota


class TrackingManager:

    def __init__(self, arduino):
        self.trackers      = []
        self.puntaje_total = 0
        self.throws        = 0
        self.last_score    = 0
        self.arduino       = arduino

    def reset(self):
        self.trackers      = []
        self.puntaje_total = 0
        self.throws        = 0
        self.last_score    = 0
        TrackerPelota._id_counter = 0
        print("Reset completo")

    def actualizar(self, detecciones):
        trackers_actualizados = set()
        detecciones_asignadas = set()

        if self.trackers and detecciones:
            matriz = []
            for det in detecciones:
                fila = []
                for t in self.trackers:
                    d = np.sqrt((det["cx"] - t.cx) ** 2 + (det["cy"] - t.cy) ** 2)
                    fila.append(d)
                matriz.append(fila)

            while True:
                min_dist = float('inf')
                best_i = best_j = -1
                for i, fila in enumerate(matriz):
                    if i in detecciones_asignadas:
                        continue
                    for j, d in enumerate(fila):
                        t = self.trackers[j]
                        if t.id in trackers_actualizados:
                            continue
                        if d < min_dist:
                            min_dist = d
                            best_i, best_j = i, j

                if best_i == -1 or min_dist > DISTANCIA_MISMA_PELOTA:
                    break

                det = detecciones[best_i]
                t   = self.trackers[best_j]
                t.actualizar(det["cx"], det["cy"], det["color_sector"], det["puntos"])
                trackers_actualizados.add(t.id)
                detecciones_asignadas.add(best_i)

                if not t.confirmada and t.tiempo_visible() >= TIEMPO_CONFIRMACION:
                    t.confirmada     = True
                    t.puntos_sumados = det["puntos"]
                    self.throws     += 1
                    self.last_score  = det["puntos"]
                    self.puntaje_total += self.last_score
                    print(f"Pelota confirmada en {det['color_sector']} +{self.last_score}pts | Total: {self.puntaje_total}")
                    mensaje = f"{self.throws},{self.last_score},{self.puntaje_total}\n"
                    self.arduino.write(mensaje.encode())

        for i, det in enumerate(detecciones):
            if i not in detecciones_asignadas and len(self.trackers) < MAX_PELOTAS:
                from tracker import TrackerPelota
                nuevo = TrackerPelota(det["cx"], det["cy"], det["color_sector"], det["puntos"])
                self.trackers.append(nuevo)
                print(f"Nueva pelota en {det['color_sector']}")

        self.trackers = [t for t in self.trackers if t.ausencia() < TIEMPO_OLVIDO]